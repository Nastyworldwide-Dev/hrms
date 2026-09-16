"""A late check-out repair is automation's rebuild, never HR's own edit.

Live, 9 Sep 2026: a day read "Present (HR)" although no person had touched it.
`Attendance.claim_hr_ownership_on_amend` turns any amendment into HR's row
unless the caller says automation is doing it, and the late check-out repair
(hrms/overrides/remote_checkin_request_hooks.py) never said so. Once a day is
HR's, every automatic fix — recovery, nightly, ERP backfill — leaves it alone,
which is exactly how August stayed broken.

Source-level pin: the repair must mark the row through the one shared helper
BEFORE it hands the row to the engine.

    PYTHONPATH=. python3 hrms/tests/test_late_checkout_rebuild_is_automation.py
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
HOOKS = HRMS / "overrides" / "remote_checkin_request_hooks.py"
HELPER = "mark_automation_rebuild"


def _calls(node) -> list:
	return [n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)] + [
		n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
	]


class TestLateCheckoutRebuildIsAutomation(unittest.TestCase):
	def setUp(self):
		self.source = HOOKS.read_text(encoding="utf-8")
		self.tree = ast.parse(self.source)

	def test_the_helper_is_imported_from_its_one_home(self):
		imports = [
			n
			for n in ast.walk(self.tree)
			if isinstance(n, ast.ImportFrom) and any(a.name == HELPER for a in n.names)
		]
		self.assertTrue(imports, f"{HELPER} is not imported")
		self.assertEqual(imports[0].module, "hrms.hr.doctype.attendance.attendance")

	def test_every_rebuild_marks_itself_before_asking_the_engine(self):
		rebuilds = [
			fn
			for fn in ast.walk(self.tree)
			if isinstance(fn, ast.FunctionDef) and "mark_attendance_for_shift_logs" in _calls(fn)
		]
		self.assertTrue(rebuilds, "no rebuild site found — did the repair move?")
		for fn in rebuilds:
			with self.subTest(function=fn.name):
				calls = _calls(fn)
				self.assertIn(HELPER, calls, f"{fn.name} rebuilds without saying it is automation")
				self.assertLess(
					calls.index(HELPER),
					calls.index("mark_attendance_for_shift_logs"),
					f"{fn.name} marks the row after the engine already used it",
				)


if __name__ == "__main__":
	unittest.main()
