"""Guards on the Employee Issue row scope: HR by delegation, IDENTITY by the
canonical resolver — and never by a raw user_id compare.

`_unrestricted` here must be a pure delegation to `hrms.hr.utils.is_hr_operator`
— the one implementation of the HR_ROLES rule that also feeds the PWA's issue
board gate via `get_current_user_info().is_hr`. A private copy here can drift
from the list the frontend renders against, which is exactly what happened
before consolidation.

The behaviour tests at the bottom pin the CREATE gate (15 Sep 2026): a user
with extra roles — an approver, a System Manager, an "HR (Instance)" holder —
filed an Employee Issue in Nadi and was told "You need the 'create' permission
on Employee Issue". Two causes, both in `has_permission` here: every non-HR
ptype outside READ_PTYPES was refused, `create` included, so anyone below HR
could not file their OWN ticket; and the company fence read `doc.company`,
which the PWA never sends and `fetch_from` fills only AFTER the create check,
so an HR user fenced to several companies (no single user default) was refused
on a blank. Now an unsaved row is fenced on its employee's company, and a
non-HR caller may create exactly one shape of ticket: their own.

AST-based and bench-free: run as `python3 hrms/tests/test_employee_issue_row_scope.py`.
"""

import ast
import sys
import unittest
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import employee_issue_row_scope as scope

SOURCE = Path(__file__).resolve().parent.parent / "overrides" / "employee_issue_row_scope.py"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestUnrestrictedDelegates(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = _function(self.tree, "_unrestricted")

	def test_delegates_to_the_one_implementation(self):
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"is_hr_operator",
			calls,
			"_unrestricted must call hrms.hr.utils.is_hr_operator — the one "
			"implementation of the HR_ROLES rule",
		)

	def test_carries_no_private_copy_of_the_role_rule(self):
		names = {node.id for node in ast.walk(self.fn) if isinstance(node, ast.Name)}
		self.assertNotIn(
			"HR_ROLES",
			names,
			"_unrestricted re-implements the role intersection instead of "
			"delegating — the drift this guard exists to prevent",
		)


class TestIdentityIsResolvedNotCompared(unittest.TestCase):
	"""The document check must ask "who is this" exactly as the list asks it.

	`has_permission` read the Employee's user_id and compared it raw, while the
	list query in the same file resolved identity through `_own_employees`. Two
	answers to one question, and the raw one FAILS OPEN in both directions the
	canonical resolver exists to close: an offboarded employee whose login is
	still enabled keeps reading their old tickets after the list has stopped
	showing them, and where two Active Employees claim one login — which the
	resolver refuses outright, because guessing one hands over the other's data —
	the raw compare says yes to BOTH people's rows.

	The list returns `1=0` for those callers. The document API did not, so a
	confidential HR case could be opened by name.

	AST-based, so it pins the SHAPE of the check rather than one phrasing of it.
	"""

	def setUp(self):
		self.fn = _function(ast.parse(SOURCE.read_text()), "has_permission")

	def test_the_check_calls_the_canonical_resolver(self):
		called = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"_own_employees",
			called,
			"has_permission must resolve identity through the canonical helper defined in this "
			"same file, not re-derive it",
		)

	def test_the_check_never_reads_user_id_itself(self):
		"""A raw read of that column IS the defect — not a style preference.
		`_own_employees` normalises the value, requires Active, and refuses a
		duplicate claim; a bare compare does none of those."""
		for node in ast.walk(self.fn):
			if isinstance(node, ast.Constant) and node.value == "user_id":
				self.fail(
					"has_permission reads user_id directly. That compare is case-sensitive, "
					"status-blind and answers yes to both claimants of a duplicated login — "
					"use _own_employees, which is eighty lines above it."
				)


# --- the create gate, as the PWA exercises it ---------------------------------

ME, PEER, OTHER_CO = "HR-EMP-ME", "HR-EMP-PEER", "HR-EMP-FAR"
COMPANY = {ME: "Co A", PEER: "Co A", OTHER_CO: "Co B"}


def _new_issue(employee):
	"""What Nadi's form sends: own employee, no company, unsaved."""
	return frappe._dict(doctype="Employee Issue", name=None, __islocal=1, employee=employee, company=None)


class _CreateGate(unittest.TestCase):
	hr = False
	fence: ClassVar[list] = []

	def setUp(self):
		self.session = patch.object(frappe, "session", frappe._dict(user="me@example.com"))
		self.session.start()
		self.patches = [
			patch.object(scope, "is_hr_operator", return_value=self.hr),
			patch.object(scope, "own_employees", return_value=[ME]),
			patch.object(scope, "allowed_companies", return_value=list(self.fence)),
			patch.object(frappe.db, "get_value", side_effect=lambda dt, name, field: COMPANY.get(name)),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in self.patches:
			p.stop()
		self.session.stop()

	def allowed(self, employee, ptype="create"):
		return scope.has_permission(_new_issue(employee), ptype, "me@example.com")


class TestPlainEmployeeFilesTheirOwnTicket(_CreateGate):
	def test_own_ticket_is_allowed(self):
		self.assertTrue(self.allowed(ME))

	def test_a_ticket_in_a_colleague_name_is_refused(self):
		self.assertFalse(self.allowed(PEER))

	def test_create_is_the_only_mutation_staff_get(self):
		for ptype in ("write", "delete", "submit", "cancel"):
			self.assertFalse(self.allowed(ME, ptype), ptype)

	def test_staff_still_read_their_own(self):
		self.assertTrue(self.allowed(ME, "read"))


class TestApproverOrSystemManagerIsStillAnEmployee(_CreateGate):
	"""Extra roles are not HR; they must not lose what a plain employee has."""

	def test_own_ticket_is_allowed(self):
		self.assertTrue(self.allowed(ME))

	def test_colleague_ticket_is_refused(self):
		self.assertFalse(self.allowed(PEER))


class TestFencedHrIsFencedOnTheEmployeeCompany(_CreateGate):
	"""HR (Instance): two Company User Permissions, so no user default fills
	`company` and the PWA sends none. The fence must read the employee's company."""

	hr = True
	fence: ClassVar[list] = ["Co A"]

	def test_own_ticket_with_blank_company_is_allowed(self):
		self.assertTrue(self.allowed(ME))

	def test_a_same_company_colleague_is_allowed(self):
		self.assertTrue(self.allowed(PEER))

	def test_another_company_employee_is_refused_even_with_blank_company(self):
		self.assertFalse(self.allowed(OTHER_CO))

	def test_a_stored_company_outside_the_fence_is_refused(self):
		doc = frappe._dict(doctype="Employee Issue", name="EI-1", employee=ME, company="Co B")
		self.assertFalse(scope.has_permission(doc, "read", "me@example.com"))


class TestNoEmployeeRecordFailsClosed(_CreateGate):
	def test_a_login_with_no_active_employee_cannot_create(self):
		with patch.object(scope, "own_employees", return_value=[]):
			self.assertFalse(self.allowed(ME))


if __name__ == "__main__":
	unittest.main()
