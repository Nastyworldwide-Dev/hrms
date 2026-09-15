"""An Attendance Request tells its approver it exists, and tells the employee the decision.

Every other request type the Nadi PWA files raises a PWA Notification when it
is filed and again when it is decided — Leave, Expense, Shift, OT, Replacement
Leave Claim (hrms/mixins/pwa_notifications.py). Attendance Request raised
none. Walked on fresh.local, 15 Sep 2026:

    Attendance Request  notified on create   []
    Attendance Request  notified on approve  []

A draft sat in a list until the manager happened to scroll past, and the
employee could not tell "waiting" from "lost" — the same silence OT Request
had before test_pwa_notifications. Attendance Request routes like OT Request
(reports_to manager, then HR — hrms.api.approval._is_routed_approver), so it
takes the same recipient resolution rather than inventing an approver field.

Bench-free: the mixin is imported under the frappe stub and driven directly;
the controller's wiring is read from the AST.

    python3 hrms/tests/test_attendance_request_notifies.py
"""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.mixins.pwa_notifications import PWANotificationsMixin

CONTROLLER = (
	pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/attendance_request/attendance_request.py"
)


class _AttendanceRequest(PWANotificationsMixin):
	doctype = "Attendance Request"
	employee = "HR-EMP-1"

	def _get_ot_approver(self):
		return "manager@example.com"

	def get(self, field):
		return getattr(self, field, None)


class TestTheMixinKnowsAttendanceRequest(unittest.TestCase):
	def test_its_decision_lives_in_status(self):
		self.assertEqual(_AttendanceRequest()._get_doc_status_field(), "status")

	def test_its_approver_is_resolved_like_ot_reports_to_then_hr(self):
		self.assertEqual(_AttendanceRequest()._get_doc_approver(), "manager@example.com")


class TestTheControllerIsWired(unittest.TestCase):
	def setUp(self):
		tree = ast.parse(CONTROLLER.read_text())
		self.cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AttendanceRequest")

	def _calls(self, method):
		fn = next((n for n in self.cls.body if isinstance(n, ast.FunctionDef) and n.name == method), None)
		self.assertIsNotNone(fn, f"AttendanceRequest.{method} is missing")
		return [
			n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]

	def test_it_mixes_in_the_pwa_notifications(self):
		self.assertIn("PWANotificationsMixin", [ast.unparse(b) for b in self.cls.bases])

	def test_filing_notifies_the_approver_once(self):
		self.assertIn("notify_approver", self._calls("after_insert"))

	def test_the_decision_notifies_the_employee(self):
		self.assertIn("notify_approval_status", self._calls("on_submit"))


if __name__ == "__main__":
	unittest.main()
