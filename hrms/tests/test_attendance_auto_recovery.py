"""Attendance recovery runs itself after deploy and nightly — Nabil, 14 Sep 2026.

PYTHONPATH=. python3 hrms/tests/test_attendance_auto_recovery.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, timedelta
from types import SimpleNamespace
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
			patch.object(auto, "is_job_enqueued", return_value=False),
			patch.object(auto, "notify_hr", MagicMock()),
			patch.object(auto, "nowdate", return_value="2026-09-15"),
			patch.object(frappe, "log_error", MagicMock(return_value=MagicMock(name="ERR-1"))),
			patch.object(
				frappe, "get_single", lambda doctype: SimpleNamespace(get=lambda k, d=None: d), create=True
			),
			patch.object(auto.rec, "unclaimable_rows", lambda win, **kw: []),
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
					{
						"employee": "E4",
						"date": "2026-09-04",
						"hr": True,
						"reason": "HR-ATT-9 is a leave record",
					},
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

	def test_nightly_window_is_seven_days_ending_the_day_before_yesterday(self):
		# At midnight yesterday's night shift (19:30-03:30) is still open: leave it.
		auto.run_nightly()
		self.assertEqual({(c[1], c[2]) for c in self.calls}, {("2026-09-07", "2026-09-13")})

	def test_nightly_waits_while_the_one_time_run_is_queued_or_running(self):
		with patch.object(auto, "is_job_enqueued", return_value=True):
			self.assertIsNone(auto.run_nightly())
		self.assertEqual(self.calls, [])

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
		# E1, E2, E3 need HR; E4 is a leave day, left alone on purpose.
		self.assertEqual(title, "Attendance recovery 2026-09-15: fixed 4, 3 day(s) need HR")
		self.assertIn(
			"Left alone on purpose (leave, HR-kept, paid): 1", frappe.log_error.call_args.kwargs["message"]
		)
		auto.notify_hr.assert_called_once()

	def test_no_duplicate_summary_for_the_same_title(self):
		self.db.exists.return_value = "ERR-OLD"
		auto.run_once()
		frappe.log_error.assert_not_called()
		auto.notify_hr.assert_not_called()

	def test_never_raises(self):
		with patch.object(auto, "_run", side_effect=RuntimeError("boom")):
			self.assertIsNone(auto.run_nightly())


class TestWhatNeedsHR(unittest.TestCase):
	"""Live, 15 Sep 2026: the first run reported "758 day(s) need HR". A leave
	day, an HR-kept day or a paid day is left alone ON PURPOSE — nothing for HR
	to do — so only days held for another reason count."""

	def test_days_left_alone_on_purpose_do_not_need_hr(self):
		for reason in (
			"HR-ATT-2026-1 is a leave record",
			"HR-ATT-2026-1 is a half-day leave",
			"HR-ATT-2026-1 comes from an Attendance Request",
			"HR-ATT-2026-1 was marked by HR by hand",
			"HR-ATT-2026-1 is marked by hand, a leave, or another instance's",
			"HR-ATT-2026-1 is a draft attendance HR is keying",
			"HR-ATT-2026-1 is a draft",
			"removed by HR in Shift Attendance: HR hands it back first",
			"HR removed this day in Shift Attendance",
			"a payout depends on this day (SAL-1)",
			"payroll or approved overtime depends on this day (OT-1)",
			"approved overtime or submitted payroll depends on this day (OT-1)",
			"today or later: never touched",
		):
			self.assertFalse(auto.needs_hr({"reason": reason, "hr": True}), reason)

	def test_a_day_the_engine_could_not_fix_needs_hr(self):
		self.assertTrue(auto.needs_hr({"reason": "the engine would not mark this day: no shift", "hr": True}))
		self.assertFalse(auto.needs_hr({"reason": "rebuild failed: boom", "hr": False}))


class TestSwitchesAndRecheck(_Case):
	"""S7 (15 Sep 2026): per-family off switches read from HR Settings (a missing
	field reads as ON), and the nightly run re-checks every employee-day the
	detectors list as fixable, however old, oldest first, at most RECHECK_CAP a
	night, never today or yesterday."""

	def setUp(self):
		super().setUp()
		self.settings = {}
		self.rows = []
		patches = [
			patch.object(
				frappe,
				"get_single",
				lambda doctype: SimpleNamespace(
					get=lambda key, default=None: self.settings.get(key, default)
				),
				create=True,
			),
			patch.object(auto.rec, "unclaimable_rows", lambda win, **kw: self.flagged(win)),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def flagged(self, win):
		return [r for r in self.rows if win.start <= date.fromisoformat(r["date"]) <= win.end]

	def fixable(self, day, employee="E1"):
		return {"employee": employee, "date": day, "status": auto.rec.STATUS_FIXABLE, "family": "F1"}

	def windows(self):
		return sorted({(c[1], c[2]) for c in self.calls})

	def test_a_family_switched_off_in_hr_settings_is_skipped_and_said_so(self):
		self.settings["attendance_recovery_skip_heal"] = 1
		summary = auto.run_once()
		self.assertNotIn("heal", [c[0] for c in self.calls])
		self.assertIn("rebuild", [c[0] for c in self.calls])
		self.assertEqual(summary["steps"]["heal"]["skipped"], "switched off in HR Settings")
		self.assertIn("heal", frappe.log_error.call_args.kwargs["message"])

	def test_a_switch_field_that_does_not_exist_yet_reads_as_on(self):
		auto.run_once()
		self.assertEqual({c[0] for c in self.calls}, set(auto.AUTO_STEPS))

	def test_nightly_rechecks_flagged_days_outside_the_window_oldest_first(self):
		self.rows = [
			self.fixable("2026-08-03"),
			self.fixable("2026-08-04", "E2"),
			self.fixable("2026-08-20"),
			self.fixable("2026-09-10"),  # inside the 7-day window already
			{"employee": "E3", "date": "2026-08-10", "status": auto.rec.STATUS_NEEDS_HR, "family": "F2"},
		]
		auto.run_nightly()
		self.assertEqual(
			self.windows(),
			[("2026-08-03", "2026-08-04"), ("2026-08-20", "2026-08-20"), ("2026-09-07", "2026-09-13")],
		)
		self.assertEqual(frappe.log_error.call_count, 1)
		self.assertIn("3 flagged day(s) re-checked", frappe.log_error.call_args.kwargs["message"])

	def test_the_recheck_never_touches_today_or_yesterday_and_caps_at_200_days(self):
		day = date(2026, 8, 1)
		while day <= date(2026, 9, 15):
			for n in range(10):
				self.rows.append(self.fixable(day.isoformat(), f"E{n}"))
			day += timedelta(days=1)
		auto.run_nightly()
		starts = [w[0] for w in self.windows()]
		ends = [w[1] for w in self.windows()]
		self.assertEqual(min(starts), "2026-08-01")
		# 200 employee-days = 20 days x 10 people: the re-check stops at 20 August
		self.assertNotIn("2026-08-21", starts + ends)
		self.assertTrue(all(e <= "2026-09-13" for e in ends))

	def test_the_recheck_has_its_own_switch(self):
		self.rows = [self.fixable("2026-08-03")]
		self.settings["attendance_recovery_skip_recheck"] = 1
		auto.run_nightly()
		self.assertEqual(self.windows(), [("2026-09-07", "2026-09-13")])

	def test_e34_the_summary_has_one_line_per_family_fixed_on_purpose_needs_hr(self):
		auto.run_once()
		message = frappe.log_error.call_args.kwargs["message"]
		self.assertRegex(message, r"rebuild \(F6/F9/F13[^)]*\): fixed 2 · on purpose 2 · needs HR 4")
		self.assertRegex(message, r"rostered_shift \(F1[^)]*\): fixed 0 · on purpose 0 · needs HR 0")
		self.assertRegex(message, r"close_lone_ins \(F3[^)]*\)")


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
		# daily_long: the default queue kills a job after 300s, silently.
		self.assertIn("hrms.utils.attendance_auto_recovery.run_nightly", events["daily_long"])
		self.assertNotIn("hrms.utils.attendance_auto_recovery.run_nightly", events["daily"])


if __name__ == "__main__":
	unittest.main()
