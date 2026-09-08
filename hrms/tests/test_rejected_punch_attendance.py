"""Rejected punches remain boundaries but never contribute worked attendance.

The rejection write still sets skip_auto_attendance. The scheduler now retains
these rows so removal cannot bridge an invalid interval; pairing and linking
use the shared eligibility predicate. Full query/mark/link scenarios are in
test_ot_nonworking_hours and the native rollback probe.
"""

import ast
import logging
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

	def test_rejected_or_skipped_boundary_is_not_eligible_work(self):
		func = _function(HRMS / "utils" / "ot_calculation.py", "_is_eligible_checkin")
		scope = {"logger": logging.getLogger(__name__), "cint": lambda value: int(value or 0)}
		exec(compile(ast.Module(body=[func], type_ignores=[]), "eligibility", "exec"), scope)
		eligible = scope["_is_eligible_checkin"]
		for status in (None, "", "Approved"):
			self.assertTrue(eligible({"remote_approval_status": status}))
		for refused in (
			{"remote_approval_status": "Rejected"},
			{"remote_approval_status": "Pending"},
			{"remote_approval_status": "Approved", "skip_auto_attendance": 1},
			{"requires_remote_approval": 1},
			{"offshift": 1},
		):
			with self.subTest(refused=refused):
				self.assertFalse(eligible(refused))


if __name__ == "__main__":
	unittest.main()
