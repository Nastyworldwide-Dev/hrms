"""Company fencing on the HR endpoints that build their own queries.

Phase 3 multi-company hardening: these endpoints used to trust a
caller-supplied `employee_filters` dict, or filter by employee/approver only,
so a user of one company could read another company's rows. Each test below
pins one endpoint's company predicate, and every group carries the
counterpart test that a caller with **no** Company User Permission is
completely unaffected — nasty-live runs this code today with no Company UPs.

Bench-free: `frappe`'s surface is mocked and no site is opened, so these run
under any interpreter that can import `frappe` (same style as
`hrms/tests/test_checkin_timezone.py`). They do NOT need a bench, a database or
a site — but unlike `test_doctype_permission_integrity.py` they do import the
modules under test, so `frappe` itself must be importable.
"""

from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import (
	remote_checkin,
	roster,
)
from hrms.utils.company_scope import (
	CompanyScopeError,
	normalize_permitted,
	resolve_company_filter,
	resolve_single_company,
)

ALPHA = "Alpha Sdn Bhd"
BETA = "Beta Sdn Bhd"
USER = "hr@example.com"


# --- fake query builder -----------------------------------------------------


class Expr:
	"""A recorded predicate: comparable, and combinable like a pypika term."""

	def __init__(self, op: str, field: str, value=None):
		self.op = op
		self.field = field
		self.value = value

	def __or__(self, other):
		return Expr("or", f"{self.field}|{other.field}", (self, other))

	def __and__(self, other):
		return Expr("and", f"{self.field}&{other.field}", (self, other))

	def __repr__(self):
		return f"Expr({self.op}, {self.field}, {self.value})"


class FakeColumn:
	def __init__(self, table: str, field: str):
		self.table = table
		self.field = field

	def __eq__(self, other):
		return Expr("eq", f"{self.table}.{self.field}", other)

	def __ge__(self, other):
		return Expr("gte", f"{self.table}.{self.field}", other)

	def __le__(self, other):
		return Expr("lte", f"{self.table}.{self.field}", other)

	def __hash__(self):
		return hash((self.table, self.field))

	def isin(self, values):
		return Expr("in", f"{self.table}.{self.field}", list(values))

	def isnull(self):
		return Expr("isnull", f"{self.table}.{self.field}")

	def as_(self, _alias):
		return self


class FakeTable:
	# the table name lives in a dunder-ish slot so `Table.name` still resolves
	# to a column (pypika behaviour the endpoints rely on)
	def __init__(self, name: str):
		object.__setattr__(self, "_table_name", name)

	def __getattr__(self, field):
		return FakeColumn(object.__getattribute__(self, "_table_name"), field)

	def __getitem__(self, field):
		return FakeColumn(object.__getattribute__(self, "_table_name"), field)


class FakeQuery:
	def __init__(self, rows=None):
		self.predicates: list[Expr] = []
		self.joins: list[str] = []
		self._rows = rows if rows is not None else []

	def where(self, expr):
		self.predicates.append(expr)
		return self

	def left_join(self, table):
		self.joins.append(object.__getattribute__(table, "_table_name"))
		return _Joiner(self)

	def select(self, *_args, **_kwargs):
		return self

	def orderby(self, *_args, **_kwargs):
		return self

	def limit(self, *_args):
		return self

	def run(self, **_kwargs):
		return self._rows

	# assertion helpers
	def predicate(self, field: str) -> Expr | None:
		return next((p for p in self.predicates if p.field == field), None)


class _Joiner:
	def __init__(self, query: FakeQuery):
		self.query = query

	def on(self, _expr):
		return self.query


def fake_qb(query: FakeQuery):
	return types.SimpleNamespace(
		DocType=FakeTable,
		get_query=lambda *a, **kw: query,
		from_=lambda _table: query,
	)


def permission_error(*_args, **_kwargs):
	raise frappe.PermissionError("denied")


def company_user_permissions(companies):
	"""frappe.get_all stand-in for the caller's `allow=Company` UP rows.

	That table read is the whole derivation (see
	`hrms.utils.company_scope.get_permitted_companies`), so an empty list here
	is the real "user has no Company User Permission" state nasty-live is in
	today.
	"""

	def _get_all(doctype, *_args, **_kwargs):
		return list(companies) if doctype == "User Permission" else []

	return _get_all


def fresh_local():
	"""frappe.local stand-in — satisfies the @whitelist decorator's checks."""
	local = types.SimpleNamespace()
	local.flags = frappe._dict(in_test=False)
	return local


def patched_frappe(companies, **extra):
	"""Patch the frappe surface these endpoints touch."""
	patches = [
		patch.object(frappe, "get_all", company_user_permissions(companies)),
		patch.object(frappe, "local", fresh_local()),
		patch.object(frappe, "session", frappe._dict(user=USER)),
		patch.object(frappe, "logger", MagicMock()),
		patch.object(frappe, "throw", permission_error),
		patch.object(frappe, "bold", lambda value: value),
	]
	# create=True: `frappe.defaults`/`frappe.qb` are lazy attributes that only
	# materialise inside a bench, and these tests run without one
	patches.extend(patch.object(frappe, key, value, create=True) for key, value in extra.items())
	return patches


class ScopedFrappe:
	def __init__(self, companies, **extra):
		self._patches = patched_frappe(companies, **extra)

	def __enter__(self):
		for p in self._patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in reversed(self._patches):
			p.stop()
		return False


# --- pure helpers -----------------------------------------------------------


class TestPureHelpers(unittest.TestCase):
	def test_no_company_user_permission_means_unfenced(self):
		self.assertIsNone(normalize_permitted([]))
		self.assertIsNone(normalize_permitted(None))
		# rows exist but are all blank — still unfenced, never "see nothing"
		self.assertIsNone(normalize_permitted(["", None]))

	def test_permitted_rows_are_deduplicated_and_sorted(self):
		self.assertEqual(normalize_permitted([BETA, ALPHA, BETA]), [ALPHA, BETA])

	def test_unfenced_caller_gets_no_constraint(self):
		self.assertIsNone(resolve_company_filter(None, None))
		self.assertIsNone(resolve_company_filter(BETA, None))

	def test_fenced_caller_defaults_to_union_of_permitted(self):
		self.assertEqual(resolve_company_filter(None, [ALPHA, BETA]), [ALPHA, BETA])

	def test_fenced_caller_may_narrow_to_a_permitted_company(self):
		self.assertEqual(resolve_company_filter(ALPHA, [ALPHA, BETA]), [ALPHA])

	def test_fenced_caller_may_not_ask_for_another_company(self):
		with self.assertRaises(CompanyScopeError):
			resolve_company_filter(BETA, [ALPHA])

	def test_single_company_is_assumable_several_are_not(self):
		self.assertEqual(resolve_single_company([ALPHA]), ALPHA)
		self.assertIsNone(resolve_single_company([ALPHA, BETA]))
		self.assertIsNone(resolve_single_company(None))


# --- roster.get_holidays ----------------------------------------------------


class TestRosterGetHolidays(unittest.TestCase):
	def _filters_used(self, companies, employee_filters):
		captured = {}

		def get_list(_doctype, filters=None, **_kwargs):
			captured.update(filters or {})
			return []

		with ScopedFrappe(companies, get_list=get_list):
			roster.get_holidays("2026-08-01", "2026-08-31", employee_filters)
		return captured

	def test_company_predicate_added_for_fenced_caller(self):
		self.assertEqual(self._filters_used([ALPHA], {"status": "Active"})["company"], ALPHA)

	def test_union_across_permitted_companies(self):
		self.assertEqual(
			self._filters_used([ALPHA, BETA], {})["company"],
			["in", [ALPHA, BETA]],
		)

	def test_another_companys_filter_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._filters_used([ALPHA], {"company": BETA})

	def test_caller_without_company_user_permission_is_unaffected(self):
		self.assertEqual(self._filters_used([], {"status": "Active"}), {"status": "Active"})

	def test_caller_cannot_smuggle_an_operator_filter(self):
		with self.assertRaises(frappe.PermissionError):
			self._filters_used([ALPHA], {"company": ["in", [ALPHA, BETA]]})


# --- roster.get_leaves / get_shifts ----------------------------------------


class TestRosterQueries(unittest.TestCase):
	def _run(self, fn, companies, employee_filters):
		query = FakeQuery()
		with ScopedFrappe(companies, qb=fake_qb(query)):
			fn(query, employee_filters)
		return query

	def _leaves(self, companies, employee_filters):
		return self._run(
			lambda _q, f: roster.get_leaves("2026-08-01", "2026-08-31", f),
			companies,
			employee_filters,
		)

	def _shifts(self, companies, employee_filters):
		return self._run(
			lambda _q, f: roster.get_shifts("2026-08-01", "2026-08-31", f, {}),
			companies,
			employee_filters,
		)

	def test_leaves_are_fenced_to_the_permitted_company(self):
		predicate = self._leaves([ALPHA], {}).predicate("Employee.company")
		self.assertEqual((predicate.op, predicate.value), ("eq", ALPHA))

	def test_leaves_span_the_union_when_several_are_permitted(self):
		predicate = self._leaves([ALPHA, BETA], {}).predicate("Employee.company")
		self.assertEqual((predicate.op, predicate.value), ("in", [ALPHA, BETA]))

	def test_leaves_refuse_another_companys_filter(self):
		with self.assertRaises(frappe.PermissionError):
			self._leaves([ALPHA], {"company": BETA})

	def test_leaves_unchanged_without_a_company_user_permission(self):
		query = self._leaves([], {"department": "Ops"})
		self.assertIsNone(query.predicate("Employee.company"))
		self.assertIsNotNone(query.predicate("Employee.department"))

	def test_shifts_are_fenced_to_the_permitted_company(self):
		predicate = self._shifts([ALPHA], {}).predicate("Employee.company")
		self.assertEqual((predicate.op, predicate.value), ("eq", ALPHA))

	def test_shifts_refuse_another_companys_filter(self):
		with self.assertRaises(frappe.PermissionError):
			self._shifts([ALPHA], {"company": BETA})

	def test_shifts_unchanged_without_a_company_user_permission(self):
		self.assertIsNone(self._shifts([], {}).predicate("Employee.company"))


# --- roster.get_default_company --------------------------------------------


class TestRosterDefaultCompany(unittest.TestCase):
	def _default(self, companies):
		defaults = types.SimpleNamespace(get_user_default=lambda _key: "User Default Co")
		with ScopedFrappe(companies, defaults=defaults):
			return roster.get_default_company()

	def test_user_default_kept_when_caller_is_unfenced(self):
		self.assertEqual(self._default([]), "User Default Co")

	def test_single_permitted_company_wins_over_the_user_default(self):
		self.assertEqual(self._default([ALPHA]), ALPHA)

	def test_nothing_is_preselected_when_several_are_permitted(self):
		self.assertEqual(self._default([ALPHA, BETA]), "")


# --- remote_checkin approver queries ---------------------------------------


class TestRemoteCheckinPending(unittest.TestCase):
	def _query(self, companies, fn):
		query = FakeQuery(rows=[])
		with ScopedFrappe(companies, qb=fake_qb(query)):
			fn()
		return query

	def test_pending_list_is_fenced_by_the_requesters_company(self):
		query = self._query([ALPHA], remote_checkin.list_pending_for_approver)
		predicate = query.predicate("Employee.company")
		self.assertEqual((predicate.op, predicate.value), ("in", [ALPHA]))
		self.assertIn("Employee", query.joins)

	def test_pending_list_spans_permitted_companies(self):
		predicate = self._query([ALPHA, BETA], remote_checkin.list_pending_for_approver).predicate(
			"Employee.company"
		)
		self.assertEqual(predicate.value, [ALPHA, BETA])

	def test_being_named_approver_still_requires_the_approver_predicate(self):
		query = self._query([ALPHA], remote_checkin.list_pending_for_approver)
		self.assertEqual(query.predicate("Remote Checkin Request.approver").value, USER)
		self.assertEqual(query.predicate("Remote Checkin Request.status").value, "Pending")

	def test_pending_list_unchanged_without_a_company_user_permission(self):
		query = self._query([], remote_checkin.list_pending_for_approver)
		self.assertIsNone(query.predicate("Employee.company"))
		self.assertEqual(query.joins, [])

	def test_badge_count_uses_the_same_fence_as_the_list(self):
		query = FakeQuery(rows=[[3]])
		with ScopedFrappe([ALPHA], qb=fake_qb(query)):
			self.assertEqual(remote_checkin.get_pending_count(), 3)
		self.assertEqual(query.predicate("Employee.company").value, [ALPHA])

	def test_badge_count_unchanged_without_a_company_user_permission(self):
		query = FakeQuery(rows=[[7]])
		with ScopedFrappe([], qb=fake_qb(query)):
			self.assertEqual(remote_checkin.get_pending_count(), 7)
		self.assertIsNone(query.predicate("Employee.company"))


# --- leave control panel default company ------------------------------------


class TestLeaveControlPanelDefaultCompany(unittest.TestCase):
	def _scoped_default(self, companies):
		from hrms.hr.doctype.leave_control_panel import leave_control_panel as lcp

		panel = lcp.LeaveControlPanel.__new__(lcp.LeaveControlPanel)
		with ScopedFrappe(companies), patch.object(lcp, "get_default_company", lambda: "User Default Co"):
			return lcp.LeaveControlPanel.get_scoped_default_company(panel)

	def test_erpnext_default_kept_when_caller_is_unfenced(self):
		self.assertEqual(self._scoped_default([]), "User Default Co")

	def test_single_permitted_company_replaces_the_erpnext_default(self):
		self.assertEqual(self._scoped_default([ALPHA]), ALPHA)

	def test_no_company_is_assumed_when_several_are_permitted(self):
		self.assertIsNone(self._scoped_default([ALPHA, BETA]))


if __name__ == "__main__":
	unittest.main()
