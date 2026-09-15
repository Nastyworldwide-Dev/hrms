"""The approver may cancel an approved request — including what it created.

Nabil, 14 Sep 2026: HR and the request's approver (named field or reports_to
manager) CAN cancel an approved request of any type. hrms.api.approval.finalize
elevates a routed approver for the cancel and approved_request_guard admits
them — and then the cancel died anyway, found by walking the lifecycle on
fresh.local as the reports_to manager (Employee role only):

    Attendance Request  cancel approved as approver  REFUSED PermissionError
    Shift Request       cancel approved as approver  REFUSED PermissionError

`on_cancel` cascades into the rows the approval created — Attendance, Shift
Assignment — with a bare `.cancel()`, so the child's DocPerm check ran against
a manager who holds no `cancel` on Attendance or Shift Assignment. The
authority question was already settled one level up (the guard let this
person cancel THIS request); the cascade only undoes what that approval did.
The same shape Leave Application already has: its attendance is cancelled
through db.set_value, its ledger entry is written with ignore_permissions.

Bench-free: `on_cancel` is lifted from each controller by AST and run against
a fake child whose cancel() refuses unless it was told to ignore permissions.

    python3 hrms/tests/test_approver_cancel_cascades_elevated.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

HR = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype"
CONTROLLERS = {
	"Attendance Request": (
		HR / "attendance_request/attendance_request.py",
		"AttendanceRequest",
		"Attendance",
	),
	"Shift Request": (HR / "shift_request/shift_request.py", "ShiftRequest", "Shift Assignment"),
}


def _lift_on_cancel(path, class_name, namespace):
	tree = ast.parse(path.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "on_cancel")
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
	return namespace["on_cancel"]


class _Child:
	"""A created row whose cancel() behaves like Frappe's for a user holding
	no `cancel` DocPerm on it: refused unless the caller elevated it."""

	def __init__(self):
		self.flags = SimpleNamespace(ignore_permissions=False)
		self.cancelled = False

	def cancel(self):
		if not self.flags.ignore_permissions:
			raise PermissionError("no cancel permission on the created row")
		self.cancelled = True


class TestApproverCancelCascadesElevated(unittest.TestCase):
	def _run(self, doctype):
		path, class_name, child_doctype = CONTROLLERS[doctype]
		child = _Child()
		frappe = MagicMock()
		frappe.get_all.return_value = [{"name": "CHILD-1"}]
		frappe.db.get_all.return_value = [{"name": "CHILD-1"}]
		frappe.get_doc.return_value = child
		on_cancel = _lift_on_cancel(path, class_name, {"frappe": frappe, "logger": MagicMock()})
		request = SimpleNamespace(name="REQ-1", employee="HR-EMP-1", doctype=doctype)
		on_cancel(request)
		return child, frappe, child_doctype

	def test_attendance_request_cancels_its_attendance_without_a_docperm_on_attendance(self):
		child, frappe, child_doctype = self._run("Attendance Request")
		self.assertTrue(child.cancelled, "the approved request's Attendance row must be cancelled")
		frappe.get_doc.assert_called_once_with(child_doctype, "CHILD-1")

	def test_shift_request_cancels_its_assignment_without_a_docperm_on_shift_assignment(self):
		child, frappe, child_doctype = self._run("Shift Request")
		self.assertTrue(child.cancelled, "the approved request's Shift Assignment must be cancelled")
		frappe.get_doc.assert_called_once_with(child_doctype, "CHILD-1")


if __name__ == "__main__":
	unittest.main()
