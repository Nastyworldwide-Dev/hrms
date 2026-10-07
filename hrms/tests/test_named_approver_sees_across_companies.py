"""A named approver sees and decides a report's requests whatever company either is in.

REPORTED 7 Oct 2026 (HR): "make the approval list show everything where the user is the named
approver, regardless of company. Amran won't be the last cross-entity manager (Dubai, South
Africa)." Amran sits in TNME; his reports sit in other companies and name him as their approver;
he saw none of their requests in Nadi.

The rule: the company fence is for HR SIGHT only. Anyone on an employee's approval line (the
named approver, the reports_to manager, the chain levels — hrms.hr.utils.get_designated_approvers)
sees and decides that employee's requests in any company. A company-fenced HR user stays fenced
for what they see only BECAUSE they are HR.

Four things each said no on a company, proven on fresh.local (approver in Company B holding an
allow=Company User Permission for B, report in Company A naming him):

  1. get_employees_routed_to walked down only through the caller's own companies;
  2. approval._request_read_allowed refused on company before asking who routes the request;
  3. the remote check-in queue fenced the WHOLE query, the routed arm included;
  4. Frappe's own User Permission check on the `company` Link field (ignore_user_permissions
     was off on six request doctypes), so frappe.has_permission was False.

Fixing (4) removes the native Company fence from HR on those doctypes, so the row scopes restate
it in code; those tests are here too.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_named_approver_sees_across_companies.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from _fake_document import FakeDocument, fake_employees

import frappe

from hrms.api import approval, remote_checkin
from hrms.hr import utils as hr_utils
from hrms.overrides import approval_row_scope, company_scope, ot_row_scope

ROOT = pathlib.Path(__file__).resolve().parents[1]

CO_A = "CO-A"
CO_B = "CO-B"
CO_C = "CO-C"

BOSS = "boss@example.com"  # Amran: company B
BOSS_EMP = "HR-EMP-BOSS"
STAFF = "HR-EMP-STAFF"  # company A, names BOSS
STRANGER = "stranger@example.com"
HR = "hr@example.com"

#: the Employee table for the walk. STAFF names BOSS and reports to him; MIDDLE reports to STAFF
#: (a second rung, in a third company); FAR reports to MIDDLE (a third rung: past the default
#: two levels, so it must NOT route to BOSS); LOOSE names somebody else entirely.
ORG = {
	BOSS_EMP: {"user_id": BOSS, "leave_approver": None, "reports_to": None, "company": CO_B},
	STAFF: {"user_id": "staff@example.com", "leave_approver": BOSS, "reports_to": BOSS_EMP, "company": CO_A},
	"HR-EMP-MIDDLE": {
		"user_id": "middle@example.com",
		"leave_approver": None,
		"reports_to": STAFF,
		"company": CO_C,
	},
	"HR-EMP-FAR": {
		"user_id": "far@example.com",
		"leave_approver": None,
		"reports_to": "HR-EMP-MIDDLE",
		"company": CO_A,
	},
	"HR-EMP-LOOSE": {
		"user_id": "loose@example.com",
		"leave_approver": "someone.else@example.com",
		"reports_to": None,
		"company": CO_A,
	},
}


def _db(rows=None):
	db = MagicMock()
	db.escape.side_effect = lambda value: f"'{value}'"
	db.get_value.side_effect = fake_employees(rows or {})
	return db


def _fence(mapping):
	"""allowed_companies stand-in: {user: [companies]}; anyone else is unfenced."""

	def allowed(user=None):
		return list(mapping.get(user or frappe.session.user, []))

	return allowed


class _Org:
	"""The frappe surface the downward walk and the upward check read, backed by ORG."""

	def __init__(self, fence):
		self.fence = fence

	def __enter__(self):
		db = MagicMock()
		db.get_value.side_effect = self._get_value
		self.patches = [
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(hr_utils, "own_employees", side_effect=self._own_employees),
			patch.object(company_scope, "allowed_companies", side_effect=_fence(self.fence)),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()

	def _own_employees(self, user=None):
		login = (user or "").strip().lower()
		return [name for name, row in ORG.items() if (row["user_id"] or "").lower() == login]

	def _get_value(self, doctype, filters, fieldname=None, **kwargs):
		if doctype != "Employee":
			return None
		row = ORG.get(filters if isinstance(filters, str) else "")
		if not row:
			return None
		if kwargs.get("as_dict"):
			wanted = fieldname if isinstance(fieldname, list) else [fieldname]
			return frappe._dict({key: row.get(key) for key in wanted})
		return row.get(fieldname)

	def _get_all(self, doctype, filters=None, pluck=None, fields=None, **kwargs):
		if doctype != "Employee":
			return []
		matched = [
			{"status": "Active", **row, "name": name}
			for name, row in ORG.items()
			if all(self._matches({**row, "name": name}, key, want) for key, want in (filters or {}).items())
		]
		if pluck:
			return [row[pluck] for row in matched]
		return [frappe._dict({key: row.get(key) for key in (fields or ["name"])}) for row in matched]

	@staticmethod
	def _matches(row, key, want):
		value = row.get(key)
		if isinstance(want, list | tuple) and len(want) == 2 and want[0] == "in":
			return value in want[1]
		return value == want


class TestTheWalkIgnoresTheCompanyFence(unittest.TestCase):
	"""get_employees_routed_to: cause 1."""

	def _routed(self, fence):
		with _Org(fence):
			return hr_utils.get_employees_routed_to(BOSS, "leave_approver", "leave_approvers")

	def test_a_report_in_another_company_is_routed_to_a_fenced_approver(self):
		"""The reported defect: BOSS is fenced to company B, STAFF sits in company A."""
		self.assertIn(STAFF, self._routed({BOSS: [CO_B]}))

	def test_the_fenced_and_the_unfenced_approver_see_the_same_people(self):
		self.assertEqual(sorted(self._routed({BOSS: [CO_B]})), sorted(self._routed({})))

	def test_the_second_rung_crosses_companies_too(self):
		"""MIDDLE (company C) reports to STAFF (company A) who names BOSS (company B)."""
		self.assertIn("HR-EMP-MIDDLE", self._routed({BOSS: [CO_B]}))

	def test_nothing_widens_beyond_the_approval_line(self):
		"""Dropping the fence must not admit people the line does not reach: LOOSE names
		someone else, and FAR is a third rung, past the default two levels."""
		routed = self._routed({BOSS: [CO_B]})
		self.assertNotIn("HR-EMP-LOOSE", routed)
		self.assertNotIn("HR-EMP-FAR", routed)


def _request(doctype="Attendance Request", **fields):
	return FakeDocument(doctype, name="REQ-0001", employee=STAFF, company=CO_A, **fields)


class TestRequestReadAllowed(unittest.TestCase):
	"""approval._request_read_allowed: cause 2."""

	def _allowed(self, doc, user, *, fence, roles=("Employee",), designated=(), has_permission=True):
		with (
			patch.object(frappe, "db", _db({STAFF: {"company": CO_A}})),
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(frappe, "get_roles", return_value=list(roles)),
			patch.object(frappe, "has_permission", return_value=has_permission),
			patch.object(company_scope, "allowed_companies", side_effect=_fence(fence)),
			patch.object(approval, "get_designated_approvers", return_value=list(designated)),
		):
			return approval._request_read_allowed(doc)

	def test_a_routed_approver_reads_another_companys_request(self):
		self.assertTrue(self._allowed(_request(), BOSS, fence={BOSS: [CO_B]}, designated=[BOSS]))

	def test_the_named_approver_on_a_leave_application_reads_it(self):
		"""Amran's own case: the leave names him in `leave_approver`."""
		doc = _request("Leave Application", leave_approver=BOSS)
		self.assertTrue(self._allowed(doc, BOSS, fence={BOSS: [CO_B]}))

	def test_someone_not_on_the_line_is_still_fenced_out(self):
		self.assertFalse(self._allowed(_request(), STRANGER, fence={STRANGER: [CO_B]}, designated=[BOSS]))

	def test_a_fenced_hr_user_off_the_line_stays_fenced(self):
		"""HR sight is exactly what the company fence is for."""
		self.assertFalse(
			self._allowed(_request(), HR, fence={HR: [CO_B]}, roles=("HR Manager",), designated=[BOSS])
		)

	def test_a_fenced_hr_user_on_the_line_reads_it(self):
		self.assertTrue(
			self._allowed(_request(), HR, fence={HR: [CO_B]}, roles=("HR Manager",), designated=[HR])
		)

	def test_a_fenced_hr_user_inside_the_fence_reads_it(self):
		self.assertTrue(self._allowed(_request(), HR, fence={HR: [CO_A]}, roles=("HR Manager",)))

	def test_native_refusal_still_wins_for_a_routed_approver(self):
		"""Routing never replaces `has_permission`: a doc the approver may not read natively stays
		unread, whatever company it is in."""
		self.assertFalse(
			self._allowed(_request(), BOSS, fence={BOSS: [CO_B]}, designated=[BOSS], has_permission=False)
		)

	def test_an_unfenced_user_is_unchanged(self):
		self.assertTrue(self._allowed(_request(), STRANGER, fence={}))


#: --- the remote check-in queue (cause 3) -----------------------------------------------------


class _Expr:
	"""A recorded predicate that can be evaluated against a row, like a pypika term."""

	def __init__(self, evaluate):
		self.evaluate = evaluate

	def __and__(self, other):
		return _Expr(lambda row: self.evaluate(row) and other.evaluate(row))

	def __or__(self, other):
		return _Expr(lambda row: self.evaluate(row) or other.evaluate(row))


class _Column:
	def __init__(self, key):
		self.key = key

	def __eq__(self, other):
		return _Expr(lambda row: row.get(self.key) == other)

	def __hash__(self):
		return hash(self.key)

	def isin(self, values):
		values = list(values)
		return _Expr(lambda row: row.get(self.key) in values)

	def as_(self, _alias):
		return self


class _Table:
	def __init__(self, name):
		object.__setattr__(self, "_name", name)

	def __getattr__(self, field):
		return _Column(f"{object.__getattribute__(self, '_name')}.{field}")

	__getitem__ = __getattr__


class _Query:
	def __init__(self):
		self.where_clauses: list[_Expr] = []

	def where(self, expr):
		self.where_clauses.append(expr)
		return self

	def left_join(self, _table):
		return self

	def on(self, _expr):
		return self

	def admits(self, row) -> bool:
		return all(clause.evaluate(row) for clause in self.where_clauses)


RCR = "Remote Checkin Request"


def _punch(employee, approver, company, status="Pending"):
	return {
		f"{RCR}.employee": employee,
		f"{RCR}.approver": approver,
		f"{RCR}.status": status,
		"Employee.company": company,
	}


class TestTheRemoteCheckinQueue(unittest.TestCase):
	def _query(self, *, fence, routed):
		built = _Query()
		qb = MagicMock()
		qb.DocType.side_effect = _Table
		qb.from_.return_value = built
		with (
			patch.object(frappe, "qb", qb, create=True),
			patch.object(frappe, "session", frappe._dict(user=BOSS)),
			patch.object(remote_checkin, "get_employees_routed_to", return_value=list(routed)),
			patch.object(remote_checkin, "permitted_company_filter", return_value=fence),
		):
			remote_checkin._pending_for_approver_query(BOSS)
		return built

	def test_the_routed_arm_is_not_fenced(self):
		"""A report in company A whose line reaches BOSS (fenced to B) is in his queue, though
		the request is stamped with a different approver."""
		query = self._query(fence=[CO_B], routed=[STAFF])
		self.assertTrue(query.admits(_punch(STAFF, "someone.else@example.com", CO_A)))

	def test_the_stamped_arm_is_still_fenced(self):
		"""A punch auto-stamped to BOSS by the resolver for an employee outside his fence is
		the algorithm's guess, not an assignment: still hidden."""
		query = self._query(fence=[CO_B], routed=[STAFF])
		self.assertFalse(query.admits(_punch("HR-EMP-OTHER", BOSS, CO_A)))

	def test_the_stamped_arm_inside_the_fence_is_listed(self):
		query = self._query(fence=[CO_B], routed=[STAFF])
		self.assertTrue(query.admits(_punch("HR-EMP-OTHER", BOSS, CO_B)))

	def test_somebody_elses_punch_is_not_listed(self):
		query = self._query(fence=[CO_B], routed=[STAFF])
		self.assertFalse(query.admits(_punch("HR-EMP-OTHER", "someone.else@example.com", CO_B)))

	def test_an_unfenced_approver_sees_the_stamped_arm_everywhere(self):
		query = self._query(fence=None, routed=[])
		self.assertTrue(query.admits(_punch("HR-EMP-OTHER", BOSS, CO_A)))

	def test_decided_requests_are_not_pending(self):
		query = self._query(fence=[CO_B], routed=[STAFF])
		self.assertFalse(query.admits(_punch(STAFF, BOSS, CO_A, status="Approved")))


#: --- the row scopes restate the fence HR lost natively (cause 4) -----------------------------


class _RowScopeCases:
	"""Shared cases; a subclass names the scope module and a doctype."""

	scope = None
	doctype = None

	def _doc(self, employee=STAFF, company=CO_A, **fields):
		return FakeDocument(self.doctype, name="REQ-0001", employee=employee, company=company, **fields)

	def _patched(self, *, fence, routed=()):
		return (
			patch.object(frappe, "db", _db({STAFF: {"company": CO_A}, BOSS_EMP: {"company": CO_B}})),
			patch.object(frappe, "session", frappe._dict(user=HR)),
			patch.object(self.scope, "_unrestricted", return_value=True),
			patch.object(self.scope, "_own_employees", return_value=[]),
			patch.object(self.scope, "get_shared", return_value=[]),
			patch.object(self.scope, "get_employees_routed_to", return_value=list(routed)),
			patch.object(company_scope, "allowed_companies", side_effect=_fence(fence)),
		)

	def _run(self, fence, fn, routed=()):
		patches = self._patched(fence=fence, routed=routed)
		for p in patches:
			p.start()
		try:
			return fn()
		finally:
			for p in reversed(patches):
				p.stop()

	def _conditions(self, fence, routed=()):
		return self._run(
			fence, lambda: self.scope.get_permission_query_conditions(self.doctype, HR), routed=routed
		)

	def _read(self, doc, fence, routed=(), ptype="read"):
		return self._run(fence, lambda: self.scope.has_permission(doc, ptype, HR), routed=routed)

	def test_fenced_hr_gets_a_company_condition_on_the_list(self):
		self.assertIn(f"`tab{self.doctype}`.`company` in ('{CO_B}')", self._conditions({HR: [CO_B]}))

	def test_unfenced_hr_gets_no_condition(self):
		self.assertEqual(self._conditions({}), "")

	def test_fenced_hr_cannot_open_another_companys_request(self):
		self.assertFalse(self._read(self._doc(), {HR: [CO_B]}))

	def test_fenced_hr_opens_a_request_inside_the_fence(self):
		self.assertTrue(self._read(self._doc(employee=BOSS_EMP, company=CO_B), {HR: [CO_B]}))

	def test_unfenced_hr_opens_any_company(self):
		self.assertTrue(self._read(self._doc(), {}))

	def test_fenced_hr_on_the_line_opens_another_companys_request(self):
		"""Off the fence by company, on it by routing: the normal checks still apply."""
		self.assertTrue(self._read(self._doc(), {HR: [CO_B]}, routed=[STAFF]))

	def test_fenced_hr_on_the_line_lists_another_companys_request(self):
		"""The list says what the document check says, or Desk lists less than it opens."""
		self.assertIn(f"'{STAFF}'", self._conditions({HR: [CO_B]}, routed=[STAFF]))

	def test_the_line_admission_stays_read_only_for_fenced_hr(self):
		self.assertFalse(self._read(self._doc(), {HR: [CO_B]}, routed=[STAFF], ptype="write"))

	def test_an_unsaved_request_is_fenced_on_the_employees_company(self):
		"""`company` is not written until the save: a new request for a company-A employee,
		filed by HR fenced to B, is refused on the employee's company."""
		new = FakeDocument(self.doctype, employee=STAFF)
		self.assertFalse(self._read(new, {HR: [CO_B]}))


class TestApprovalRowScope(_RowScopeCases, unittest.TestCase):
	scope = approval_row_scope
	doctype = "Leave Application"

	def _patched(self, *, fence, routed=()):
		return (
			*super()._patched(fence=fence, routed=routed),
			patch.object(approval_row_scope, "_report_employees", return_value=list(routed)),
		)

	def test_fenced_hr_named_as_the_approver_opens_it(self):
		doc = self._doc(leave_approver=HR)
		self.assertTrue(self._read(doc, {HR: [CO_B]}))


class TestOtRowScope(_RowScopeCases, unittest.TestCase):
	scope = ot_row_scope
	doctype = "OT Request"


class TestEveryRequestDoctypeIgnoresUserPermissionsOnCompany(unittest.TestCase):
	"""cause 4: the `company` Link on these doctypes must not be fenced natively."""

	DOCTYPES = (
		"leave_application",
		"expense_claim",
		"shift_request",
		"attendance_request",
		"ot_request",
		"replacement_leave_claim",
	)

	def test_company_field_ignores_user_permissions(self):
		for name in self.DOCTYPES:
			with self.subTest(doctype=name):
				meta = json.loads((ROOT / "hr" / "doctype" / name / f"{name}.json").read_text())
				field = next(f for f in meta["fields"] if f["fieldname"] == "company")
				self.assertEqual(
					field.get("ignore_user_permissions"),
					1,
					f"{name}.company is fenced by User Permissions: a named approver in another company "
					"cannot open the request",
				)


class TestThePatch(unittest.TestCase):
	MODULE = "hrms.patches.v16_0.approver_reads_past_company_user_permissions"

	def test_it_is_registered_after_model_sync(self):
		lines = (ROOT / "patches.txt").read_text().splitlines()
		after_sync = lines[lines.index("[post_model_sync]") :]
		self.assertTrue(
			any(line.split("#")[0].strip() == self.MODULE for line in after_sync),
			"the patch is not in [post_model_sync] of hrms/patches.txt",
		)

	def _run(self, *, flags, setters=()):
		"""execute() against a fake site; returns (set_value calls, deleted setters)."""
		import importlib

		patch_module = importlib.import_module(self.MODULE)

		db = MagicMock()
		db.exists.return_value = True
		db.get_all.return_value = [frappe._dict(name=n, value="0", owner="x", modified="y") for n in setters]
		db.get_value.side_effect = lambda doctype, filters, fields, as_dict=False: frappe._dict(
			name=f"DF-{filters['parent']}", ignore_user_permissions=flags.get(filters["parent"], 0)
		)
		deleted = []
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "delete_doc", side_effect=lambda dt, name: deleted.append(name)),
			patch.object(frappe, "clear_cache"),
		):
			patch_module.execute()
		return db.set_value.call_args_list, deleted

	def test_it_sets_the_flag_on_every_doctype_that_lacks_it(self):
		calls, _ = self._run(flags={})
		self.assertEqual(len(calls), 6)
		for call in calls:
			self.assertEqual(call.args[0], "DocField")
			self.assertEqual(call.args[2:], ("ignore_user_permissions", 1))

	def test_it_is_idempotent(self):
		flags = {
			dt: 1
			for dt in (
				"Leave Application",
				"Expense Claim",
				"Shift Request",
				"Attendance Request",
				"OT Request",
				"Replacement Leave Claim",
			)
		}
		calls, deleted = self._run(flags=flags)
		self.assertEqual(calls, [])
		self.assertEqual(deleted, [])

	def test_it_removes_a_property_setter_that_outranks_the_json(self):
		_, deleted = self._run(flags={}, setters=("PS-1",))
		self.assertEqual(deleted.count("PS-1"), 6)  # the same fake answer for each doctype


class TestTheOtSummaryReachesTheLine(unittest.TestCase):
	"""The OT summary push picks its recipient by the same rule: the line in any company, the HR
	fallback inside the company. It skipped Amran and went to HR before."""

	def _can_receive(self, *, fenced_to, on_line, line=True):
		from hrms.mixins.pwa_notifications import PWANotificationsMixin

		class _Ot(PWANotificationsMixin):
			doctype = "OT Request"
			name = "OT-1"
			employee = STAFF

			def _get_employee_user(self):
				return "staff@example.com"

		doc = _Ot()
		db = MagicMock()
		db.get_value.return_value = 1  # User.enabled
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "has_permission", return_value=True),
			patch.object(company_scope, "allowed_companies", return_value=fenced_to),
			patch.object(approval, "_is_routed_approver", return_value=on_line),
		):
			return doc._ot_approver_can_receive(BOSS, CO_A, line=line)

	def test_an_approver_on_the_line_in_another_company_receives_it(self):
		self.assertTrue(self._can_receive(fenced_to=[CO_B], on_line=True))

	def test_the_hr_fallback_stays_inside_its_company(self):
		self.assertFalse(self._can_receive(fenced_to=[CO_B], on_line=True, line=False))

	def test_nobody_off_the_line_receives_it(self):
		self.assertFalse(self._can_receive(fenced_to=[], on_line=False))


if __name__ == "__main__":
	unittest.main(verbosity=2)
