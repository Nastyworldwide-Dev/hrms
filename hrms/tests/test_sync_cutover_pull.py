"""After cutover a pull never touches the doctypes this site writes.

PYTHONPATH=. python3 hrms/tests/test_sync_cutover_pull.py
"""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.sync.cutover import LOCALLY_OWNED_AFTER_CUTOVER, plan_pull_doctypes

HRMS = pathlib.Path(__file__).resolve().parent.parent


class TestPlanPullDoctypes(unittest.TestCase):
	def test_locked_instance_pulls_everything_requested(self):
		kept, held = plan_pull_doctypes(["Employee", "Attendance", "Employee Checkin"], unlocked=False)
		self.assertEqual(kept, ["Employee", "Attendance", "Employee Checkin"])
		self.assertEqual(held, [])

	def test_unlocked_instance_holds_attendance_and_punches_back(self):
		kept, held = plan_pull_doctypes(
			["Employee", "Attendance", "Leave Allocation", "Employee Checkin"], unlocked=True
		)
		self.assertEqual(kept, ["Employee", "Leave Allocation"])
		self.assertEqual(held, ["Attendance", "Employee Checkin"])

	def test_the_locally_owned_set_is_exactly_the_two(self):
		self.assertEqual(set(LOCALLY_OWNED_AFTER_CUTOVER), {"Attendance", "Employee Checkin"})


class TestTheRunnerAsksBeforePulling(unittest.TestCase):
	def test_sync_instance_plans_its_doctypes_through_the_rule(self):
		tree = ast.parse((HRMS / "sync/runner.py").read_text())
		fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sync_instance")
		calls = {
			getattr(n.func, "id", None) or getattr(n.func, "attr", None)
			for n in ast.walk(fn)
			if isinstance(n, ast.Call)
		}
		self.assertIn(
			"plan_pull_doctypes", calls, "sync_instance must hold back locally owned doctypes after cutover"
		)
		self.assertIn("_instance_unlocked", calls, "the rule must read the real cutover switch")


class TestParityGradesOnlyWhatIsStillPulled(unittest.TestCase):
	def test_scoped_parity_report_plans_its_doctypes_through_the_rule(self):
		src = (HRMS / "sync/parity.py").read_text()
		tree = ast.parse(src)
		fn = next(
			n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_scoped_parity_report"
		)
		calls = {
			getattr(n.func, "id", None) or getattr(n.func, "attr", None)
			for n in ast.walk(fn)
			if isinstance(n, ast.Call)
		}
		self.assertIn("plan_pull_doctypes", calls, "parity must not grade doctypes the pull holds back")
		self.assertIn("_instance_unlocked", calls)
		self.assertIn(
			'report["held_back"]', ast.get_source_segment(src, fn), "the report says what was held back"
		)


if __name__ == "__main__":
	unittest.main()
