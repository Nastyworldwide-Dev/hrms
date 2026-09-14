"""Attendance recovery runs itself after deploy and nightly — Nabil, 14 Sep 2026.

PYTHONPATH=. python3 hrms/tests/test_attendance_auto_recovery.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_auto_recovery as auto

HRMS = pathlib.Path(__file__).resolve().parents[1]


class _Case(unittest.TestCase):
	def setUp(self):
		self.calls = []
		self.db = MagicMock()
		self.db.exists.return_value = None
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(auto.rec, "_PLANNERS", {s: self._planner(s) for s in auto.rec.STEPS}),
			patch.object(auto.rec, "_APPLIERS", {s: self._applier(s) for s in auto.rec.STEPS}),
			patch.object(
				auto.rec,
				"_ot_request_review",
				return_value={"hr_list": [{"employee": "E3", "date": "2026-09-01"}]},
			),
			patch.object(frappe, "set_user", MagicMock(), create=True),
			patch.object(auto, "notify_hr", MagicMock()),
			patch.object(auto, "nowdate", return_value="2026-09-15"),
			patch.object(frappe, "log_error", MagicMock(return_value=MagicMock(name="ERR-1"))),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)
		self.fail_step = None

	def _planner(self, step):
		def plan(win, for_update=False):
			self.calls.append((step, str(win.start), str(win.end), for_update))
			if step == self.fail_step:
				raise frappe.ValidationError("boom")
			held = [{"employee": "E1", "date": "2026-09-02", "hr": True}] if step == "heal" else []
			return {"planned": [], "held_back": held}

		return plan

	def _applier(self, step):
		def apply(win, plan):
			held = (
				[
					{"employee": "E2", "date": "2026-09-03", "hr": True},
					{"employee": "E1", "date": "2026-09-02", "hr": True},
				]
				if step == "rebuild"
				else []
			)
			return {"done": [1] if step in ("rebuild", "heal") else [], "held_back": held}

		return apply


class TestOrder(_Case):
	def test_runs_every_step_but_import_in_order_for_real(self):
		auto.run_once()
		steps = [c[0] for c in self.calls]
		one_window = [s for s in auto.rec.STEPS if s != "import"]
		self.assertEqual(steps, one_window * 2)
		self.assertTrue(all(c[3] is True for c in self.calls))
		self.assertEqual(self.db.commit.call_count >= len(steps), True)

	def test_one_time_window_is_august_first_to_yesterday(self):
		auto.run_once()
		windows = sorted({(c[1], c[2]) for c in self.calls})
		self.assertEqual(windows, [("2026-08-01", "2026-08-31"), ("2026-09-01", "2026-09-14")])

	def test_nightly_window_is_the_last_seven_days_to_yesterday(self):
		auto.run_nightly()
		self.assertEqual({(c[1], c[2]) for c in self.calls}, {("2026-09-08", "2026-09-14")})

	def test_a_refusing_step_stops_the_run_and_is_reported(self):
		self.fail_step = "heal"
		summary = auto.run_once()
		self.assertEqual(summary["stopped_at"], "heal")
		self.assertNotIn("skip_stamps", [c[0] for c in self.calls])
		self.db.rollback.assert_called()
		auto.notify_hr.assert_called_once()


class TestReport(_Case):
	def test_one_summary_with_fixed_count_and_hr_days(self):
		auto.run_once()
		title = frappe.log_error.call_args.kwargs["title"]
		self.assertEqual(title, "Attendance recovery 2026-09-15: fixed 4, 3 day(s) need HR")
		auto.notify_hr.assert_called_once()

	def test_no_duplicate_summary_for_the_same_title(self):
		self.db.exists.return_value = "ERR-OLD"
		auto.run_once()
		frappe.log_error.assert_not_called()
		auto.notify_hr.assert_not_called()

	def test_never_raises(self):
		with patch.object(auto, "_run", side_effect=RuntimeError("boom")):
			self.assertIsNone(auto.run_nightly())


class TestWiring(unittest.TestCase):
	def test_patch_only_enqueues_the_one_time_run(self):
		from hrms.patches.v16_0 import run_attendance_recovery_once as p

		with patch.object(frappe, "enqueue", MagicMock()) as enqueue:
			p.execute()
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.args[0], "hrms.utils.attendance_auto_recovery.run_once")
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])

	def test_patch_registered_once(self):
		lines = (HRMS / "patches.txt").read_text(encoding="utf-8").splitlines()
		self.assertEqual(
			sum(1 for l in lines if l.startswith("hrms.patches.v16_0.run_attendance_recovery_once")), 1
		)

	def test_nightly_scheduler_entry(self):
		tree = ast.parse((HRMS / "hooks.py").read_text(encoding="utf-8"))
		node = next(
			n.value
			for n in ast.walk(tree)
			if isinstance(n, ast.Assign)
			and any(getattr(t, "id", None) == "scheduler_events" for t in n.targets)
		)
		events = ast.literal_eval(node)
		self.assertIn("hrms.utils.attendance_auto_recovery.run_nightly", events["daily"])


if __name__ == "__main__":
	unittest.main()
