"""A rejected remote check-in must be excluded from auto-attendance.

Attendance marking (`ShiftType.get_employee_checkins`) selects punches by
`skip_auto_attendance = 0` and knows nothing about `remote_approval_status`.
The rejection handler used to flip only the status fields, so a punch HR
explicitly rejected still marked the employee Present with working hours —
the approval feature was cosmetic for attendance purposes.

Both halves of the contract are pinned, because either side can silently
undo it:

  * the REJECTION must set `skip_auto_attendance` on the linked check-in;
  * the ATTENDANCE FETCH must keep filtering on `skip_auto_attendance`.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent


def _function(path: pathlib.Path, name: str):
	for node in ast.walk(ast.parse(path.read_text())):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {path}")


def _set_value_dicts(func):
	"""Constant keys of every dict passed to a frappe.db.set_value call."""
	for node in ast.walk(func):
		if not isinstance(node, ast.Call) or getattr(node.func, "attr", None) != "set_value":
			continue
		for arg in node.args:
			if isinstance(arg, ast.Dict):
				yield {k.value for k in arg.keys if isinstance(k, ast.Constant)}


class TestRejectedPunchAttendance(unittest.TestCase):
	def test_rejection_sets_skip_auto_attendance(self):
		func = _function(
			HRMS / "overrides" / "remote_checkin_request_hooks.py", "propagate_approval_decision"
		)
		rejected_writes = [keys for keys in _set_value_dicts(func) if "remote_approval_status" in keys]
		self.assertTrue(rejected_writes, "expected set_value writes of remote_approval_status")
		self.assertTrue(
			any("skip_auto_attendance" in keys for keys in rejected_writes),
			"propagate_approval_decision no longer sets skip_auto_attendance — a rejected "
			"punch will feed auto-attendance again and mark the employee Present from a "
			"punch HR explicitly refused.",
		)

	def test_attendance_fetch_still_filters_on_skip_auto_attendance(self):
		"""The other half: the fetch this fix relies on must keep its filter."""
		func = _function(
			HRMS.parent / "hrms" / "hr" / "doctype" / "shift_type" / "shift_type.py",
			"get_employee_checkins",
		)
		filter_keys = {
			k.value
			for node in ast.walk(func)
			if isinstance(node, ast.Dict)
			for k in node.keys
			if isinstance(k, ast.Constant)
		}
		self.assertIn(
			"skip_auto_attendance",
			filter_keys,
			"ShiftType.get_employee_checkins dropped its skip_auto_attendance filter — "
			"the rejected-punch exclusion depends on it.",
		)


if __name__ == "__main__":
	unittest.main()
