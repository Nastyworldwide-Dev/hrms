"""INVARIANT: everyone can file their OWN requests, whatever else they hold.

Owner, 15 Sep 2026: "there are many employees, and those who have EXTRA
permission can't; normal employees can. Unfair. Everyone must be able to do
these basic things." This walks the matrix the bench probe walked on
fresh.local — every doctype the PWA files AS the employee x every user shape
the hub knows — through the three gates Frappe consults for
`has_permission(doctype, "create", <new doc>)`, with the doc built the way
Nadi's form sends it (own employee set, no company, no posting date):

  1. ROLE — a level-0 DocPerm row with create=1 for one of the user's roles.
     Frappe's `get_role_permissions` never downgrades `create` for if_owner
     (`ptype != "create"` in that loop), so any such row is enough.
  2. HOOK — the `has_permission` hook hooks.py wires for the doctype, called
     with the real function and stubbed identity/roles/fence.
  3. USER PERMISSION — a stale self allow=Employee row is the one shape that
     fails here; the realign gate re-points it on the next save.

plus the forgotten check-out API door and the case-drifted login the role
keeper rescues. Each shape must be allowed for its OWN employee; the
other-employee rules must hold unchanged: staff refused in a colleague's
name, fenced HR refused across the fence on the hooks that fence.

Employee Advance and Travel Request are not in the walk: their JSON grants
staff no create (v15.112 lock) and Nadi ships no form for them — asserted at
the bottom so the exclusion is a decision on record, not an omission.

Bench-free, must stay green:

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_everyone_can_file_own_requests.py
"""

import ast
import glob
import importlib
import json
import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms.hr.utils as hr_utils
from hrms.api import remote_checkin
from hrms.overrides import company_scope, employee_hrms_scope, employee_master
from hrms.utils.identity import normalize_login
from hrms.utils.request_access import NOT_SELF_SERVICE, PWA_REQUEST_DOCTYPES

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = HRMS_ROOT.parent

LOGIN = "me@example.com"
ME, PEER, FAR = "HR-EMP-ME", "HR-EMP-PEER", "HR-EMP-FAR"
COMPANY = {ME: "Co A", PEER: "Co A", FAR: "Co B"}
HR_SIGHT = {"HR User", "HR Manager"}

#: The user shapes the hub knows. `fence` = allow=Company User Permissions;
#: `default_company` = what Frappe's user default fills into a new doc (one
#: Company UP gives one; two give none); `user_id` = the Employee's stored
#: login; `self_up` = the allow=Employee row on the user.
SHAPES = {
	"plain Employee": {"roles": {"Employee"}},
	"Employee + approver roles (reports_to manager)": {
		"roles": {"Employee", "Leave Approver", "Expense Approver", "Shift Request Approver"}
	},
	"HR User": {"roles": {"Employee", "HR User"}},
	"HR Manager": {"roles": {"Employee", "HR Manager"}},
	"HR (Company) profile + one Company UP": {
		"roles": {"Employee", "HR User", "HR Manager", "Leave Approver", "Expense Approver", "HR (Company)"},
		"fence": ["Co A"],
		"default_company": "Co A",
	},
	"HR (Instance) + two Company UPs": {
		"roles": {"Employee", "HR User", "HR Manager", "HR (Instance)"},
		"fence": ["Co A", "Co B"],
	},
	"System Manager who is also an employee": {"roles": {"Employee", "System Manager"}},
	"user_id differs in case/whitespace from the login": {
		"roles": {"Desk User"},  # erpnext's validate_employee_role already stripped Employee
		"user_id": "  Me@Example.COM ",
	},
	"stale self allow=Employee UP": {"roles": {"Employee"}, "self_up": "HR-EMP-OLD"},
}

#: What the PWA sends: the employee field of each doctype.
EMPLOYEE_FIELD = {"Shift Swap Request": "requesting_employee"}


def _hooks_wiring() -> dict:
	tree = ast.parse((HRMS_ROOT / "hooks.py").read_text())
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == "has_permission" for t in node.targets
		):
			return ast.literal_eval(node.value)
	raise AssertionError("hooks.py has no has_permission dict")


def _docperms(doctype: str) -> list[dict]:
	for path in glob.glob(str(HRMS_ROOT / "**" / "doctype" / "*" / "*.json"), recursive=True):
		try:
			data = json.loads(pathlib.Path(path).read_text())
		except (OSError, ValueError):
			continue
		if isinstance(data, dict) and data.get("doctype") == "DocType" and data.get("name") == doctype:
			return data.get("permissions", [])
	raise AssertionError(f"no DocType JSON for {doctype}")


HOOKS = _hooks_wiring()


def _new_doc(doctype, employee, company):
	doc = frappe._dict(doctype=doctype, name=None, __islocal=1, company=company, owner=LOGIN)
	doc[EMPLOYEE_FIELD.get(doctype, "employee")] = employee
	return doc


class _Shape:
	def __init__(self, name):
		spec = SHAPES[name]
		self.name = name
		self.roles = set(spec["roles"])
		self.fence = list(spec.get("fence", []))
		self.default_company = spec.get("default_company")
		self.user_id = spec.get("user_id", LOGIN)
		self.self_up = spec.get("self_up")

	@property
	def hr(self):
		return bool(self.roles & HR_SIGHT)

	def resolves(self):
		"""Identity as hrms.utils.identity answers it: normalized login, exactly one Active claim."""
		return [ME] if normalize_login(self.user_id) == LOGIN else []


def _hook_stubs(stack: ExitStack, shape: _Shape, module):
	"""Stub the identity / role / fence primitives a hook module imported."""
	own = shape.resolves()
	stubs = {
		"sees_all_employee_data": lambda user=None: shape.hr,
		"is_hr_operator": lambda user=None: shape.hr,
		"_has_hr_access": lambda user: shape.hr,
		"own_employees": lambda user=None: list(own),
		"_get_own_employees": lambda user: list(own),
		"allowed_companies": lambda user=None: list(shape.fence),
		"get_direct_report_employees": lambda user: [],
		"get_shared": lambda *a, **k: [],
	}
	for name, fn in stubs.items():
		if hasattr(module, name):
			stack.enter_context(patch.object(module, name, side_effect=fn))
	stack.enter_context(patch.object(hr_utils, "get_direct_report_employees", side_effect=lambda user: []))
	# company_visible() reads the fence from its own module, not from the hook's import
	stack.enter_context(
		patch.object(company_scope, "allowed_companies", side_effect=lambda user=None: list(shape.fence))
	)
	stack.enter_context(patch.object(frappe, "session", frappe._dict(user=LOGIN)))
	stack.enter_context(
		patch.object(frappe.db, "get_value", side_effect=lambda dt, name, field=None, **k: COMPANY.get(name))
	)


def _role_gate(doctype, roles) -> bool:
	return any(
		row.get("create") and not row.get("permlevel") and row["role"] in roles for row in _docperms(doctype)
	)


def _hook_gate(doctype, shape, employee) -> bool:
	dotted = HOOKS[doctype]
	module = importlib.import_module(dotted.rsplit(".", 1)[0])
	fn = getattr(module, dotted.rsplit(".", 1)[1])
	doc = _new_doc(doctype, employee, shape.default_company)
	with ExitStack() as stack:
		_hook_stubs(stack, shape, module)
		return bool(fn(doc, "create", LOGIN))


def _keeper_restores_employee_role(shape) -> set:
	"""The User.validate keeper, run on the stripped role set."""
	user = frappe._dict(name=LOGIN, roles=[frappe._dict(role=r) for r in shape.roles])
	user.append_roles = lambda *rs: user.roles.extend(frappe._dict(role=r) for r in rs)
	with patch.object(employee_master, "own_employees", return_value=shape.resolves()):
		employee_master.keep_employee_role_for_linked_login(user)
	return {r.role for r in user.roles}


def _realigned_self_up(shape) -> str | None:
	"""What the self allow=Employee row names after the realign gate ran."""
	rows = [frappe._dict(name="UP-self", for_value=shape.self_up)]
	moved_to = {}
	with (
		patch.object(employee_hrms_scope, "sees_all_employee_data", return_value=shape.hr),
		patch.object(employee_hrms_scope, "own_employees", return_value=shape.resolves()),
		patch.object(frappe, "get_all", return_value=rows),
		patch.object(frappe.db, "set_value", side_effect=lambda dt, n, f, v: moved_to.__setitem__(n, v)),
		patch.object(frappe, "clear_cache"),
	):
		employee_hrms_scope.realign_self_employee_permission(LOGIN)
	return moved_to.get("UP-self", shape.self_up)


class TestEveryoneCanFileTheirOwnRequests(unittest.TestCase):
	def test_every_doctype_for_every_shape(self):
		for shape_name in SHAPES:
			shape = _Shape(shape_name)
			with self.subTest(shape=shape_name):
				roles = set(shape.roles)
				if "Employee" not in roles:
					roles = _keeper_restores_employee_role(shape)
					self.assertIn("Employee", roles, "the keeper must restore the stripped role")
				self_up = _realigned_self_up(shape) if shape.self_up else None
				if shape.self_up:
					self.assertEqual(self_up, ME, "a stale self User Permission must be re-pointed")
				for doctype in PWA_REQUEST_DOCTYPES:
					with self.subTest(shape=shape_name, doctype=doctype):
						self.assertTrue(_role_gate(doctype, roles), "role gate")
						self.assertTrue(_hook_gate(doctype, shape, ME), f"hook {HOOKS[doctype]}")
						self.assertIn(self_up, (None, ME), "user permission gate")

	def test_the_forgotten_check_out_door_is_open_for_every_shape(self):
		for shape_name in SHAPES:
			shape = _Shape(shape_name)
			with self.subTest(shape=shape_name):
				with (
					patch.object(remote_checkin, "own_employees", return_value=shape.resolves()),
					patch.object(remote_checkin, "frappe", MagicMock(session=MagicMock(user=LOGIN))),
				):
					self.assertTrue(remote_checkin._is_own_employee(ME))


class TestTheOtherEmployeeRulesStillHold(unittest.TestCase):
	def test_staff_shapes_are_refused_in_a_colleague_s_name(self):
		for shape_name in SHAPES:
			shape = _Shape(shape_name)
			if shape.hr:
				continue
			for doctype in PWA_REQUEST_DOCTYPES:
				with self.subTest(shape=shape_name, doctype=doctype):
					self.assertFalse(_hook_gate(doctype, shape, PEER))

	def test_fenced_hr_is_refused_across_the_fence_where_the_hook_fences(self):
		shape = _Shape("HR (Company) profile + one Company UP")
		for doctype in (
			"Attendance Request",
			"Compensatory Leave Request",
			"Remote Checkin Request",
			"Employee Issue",
		):
			with self.subTest(doctype=doctype):
				self.assertTrue(_hook_gate(doctype, shape, PEER), "same company")
				self.assertFalse(_hook_gate(doctype, shape, FAR), "other company")

	def test_a_login_nobody_claims_is_refused_everywhere(self):
		class _Nobody(_Shape):
			def resolves(self):
				return []

		shape = _Nobody("plain Employee")
		for doctype in PWA_REQUEST_DOCTYPES:
			if doctype in ("Leave Application", "Expense Claim", "Shift Request"):
				continue  # approval_row_scope leaves an unsaved doc to role perms + validate_staff_approver
			with self.subTest(doctype=doctype):
				self.assertFalse(_hook_gate(doctype, shape, ME))


class TestTheExclusionsAreDecisions(unittest.TestCase):
	def test_every_doctype_in_the_walk_has_a_hook_and_a_staff_create_row(self):
		for doctype in PWA_REQUEST_DOCTYPES:
			self.assertIn(doctype, HOOKS, f"{doctype} has no has_permission hook — nothing fences it")
			self.assertTrue(_role_gate(doctype, {"Employee"}), f"{doctype} JSON grants Employee no create")

	def test_employee_advance_and_travel_request_are_not_self_service_by_design(self):
		for doctype in NOT_SELF_SERVICE:
			self.assertFalse(_role_gate(doctype, {"Employee", "Employee Self Service"}), doctype)
		views = "".join(p.read_text() for p in (REPO_ROOT / "frontend" / "src" / "views").rglob("*.vue"))
		for doctype in NOT_SELF_SERVICE:
			self.assertNotIn(f'doctype="{doctype}"', views, f"the PWA ships no create form for {doctype}")

	def test_every_pwa_create_form_is_in_the_walk(self):
		views = (REPO_ROOT / "frontend" / "src" / "views").rglob("*.vue")
		import re

		targets = set()
		for path in views:
			targets.update(re.findall(r'<FormView[^>]*doctype="([^"]+)"', path.read_text()))
		self.assertTrue(targets, "no <FormView doctype=...> found — did the views move?")
		# Shift Assignment's form is detail-only: router/attendance.js dropped
		# /shift-assignments/new, so nothing in the app creates one as the employee.
		detail_only = {"Shift Assignment"}
		self.assertLessEqual(
			targets - detail_only, set(PWA_REQUEST_DOCTYPES), targets - set(PWA_REQUEST_DOCTYPES)
		)


if __name__ == "__main__":
	unittest.main()
