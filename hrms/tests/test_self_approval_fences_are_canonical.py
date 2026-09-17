"""The self-approval fences recognise the employee however their user_id is spelled.

validate_self_submission (hrms/hr/utils.py — OT Request, Replacement Leave
Claim, Shift Request, Compensatory Leave Request) and the Attendance Request,
Leave Application and Expense Claim equivalents asked "is the submitter the
employee on the request?" as `Employee.user_id == frappe.session.user`, raw.
A mirror writes user_id through db.set_value, which does not normalise, so a
row reading "  Staff@Example.com " never equals the session "staff@example.com"
— and the fence FAILS OPEN: the employee approves their own request. Listed as
the open ticket in 0b7583a19, which fixed the refusal-side twin in
remote_checkin the same way.

Every fence now asks hrms.hr.utils.is_own_employee, built on
hrms.utils.identity.own_employees; it also keeps the fence closed where
own_employees fails closed to [] (an inactive or duplicated login).

Bench-free:  python3 hrms/tests/test_self_approval_fences_are_canonical.py
"""

import ast
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms.hr.utils as hr_utils

HRMS = pathlib.Path(__file__).resolve().parents[1]
STAFF = "HR-EMP-STAFF"
SESSION = "staff@example.com"

#: file -> (class or None, function) for every self-approval fence
FENCES = {
	"hr/utils.py": (None, "validate_self_submission"),
	"hr/doctype/attendance_request/attendance_request.py": (
		"AttendanceRequest",
		"validate_for_self_approval",
	),
	"hr/doctype/leave_application/leave_application.py": ("LeaveApplication", "validate_for_self_approval"),
	"hr/doctype/expense_claim/expense_claim.py": ("ExpenseClaim", "validate_for_self_approval"),
	# Added 17 Sep 2026. The list named only the doctype validators, so the
	# decision endpoint — the PWA's whole approval path — kept the raw user_id
	# compare this test exists to forbid, and the cancel guard with it.
	"api/approval.py": (None, "_decision_access"),
	"utils/approved_request_guard.py": (None, "is_own_request"),
}


def _submit(stored_user_id, own):
	db = MagicMock()
	db.get_value.side_effect = lambda doctype, name, field=None, *a, **k: (
		stored_user_id if doctype == "Employee" and field == "user_id" else None
	)
	doc = frappe._dict(doctype="OT Request", name="OT-0001", employee=STAFF)
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "session", frappe._dict(user=SESSION)),
		patch.object(hr_utils, "own_employees", return_value=list(own)),
		patch("frappe.model.workflow.get_workflow_name", return_value=None),
	):
		hr_utils.validate_self_submission(doc)


class TestTheSharedFence(unittest.TestCase):
	def test_a_case_and_space_drifted_user_id_is_still_the_employee(self):
		with self.assertRaises(frappe.ValidationError):
			_submit("  Staff@Example.com ", own=[STAFF])

	def test_the_fence_stays_closed_when_the_resolver_cannot_answer(self):
		# own_employees returns [] for an inactive or duplicated login
		with self.assertRaises(frappe.ValidationError):
			_submit("  Staff@Example.com ", own=[])

	def test_someone_else_may_submit(self):
		_submit("other@example.com", own=["HR-EMP-OTHER"])


class TestNoFenceComparesUserIdRaw(unittest.TestCase):
	def _function(self, path, cls, name):
		tree = ast.parse((HRMS / path).read_text())
		scope = (
			tree
			if cls is None
			else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
		)
		return next(n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == name)

	def test_every_fence_asks_the_canonical_helper(self):
		for path, (cls, name) in FENCES.items():
			with self.subTest(fence=f"{path}:{name}"):
				fn = self._function(path, cls, name)
				calls = {
					n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None)
					for n in ast.walk(fn)
					if isinstance(n, ast.Call)
				}
				self.assertIn("is_own_employee", calls)
				for sub in ast.walk(fn):
					if isinstance(sub, ast.Constant) and sub.value == "user_id":
						self.fail(f"{name} reads user_id raw — use is_own_employee")


if __name__ == "__main__":
	unittest.main()
