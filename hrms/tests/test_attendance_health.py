"""HR should not discover broken attendance from staff complaints.

`run_daily_health_check` reads yesterday plus a rolling week (never today,
never with a network call) and drops ONE Error Log naming what is broken,
skipping the write entirely when the day is clean or already reported.
`health_summary` exposes the same read to HR User too, without going through
`inputs_report`'s own narrower (System Manager / HR Manager only) gate — see
`hrms/utils/attendance_health.py`'s module docstring for why.

PYTHONPATH=. python3 hrms/tests/test_attendance_health.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_health as health

TODAY = datetime(2026, 9, 14, 11, 0)
YESTERDAY = date(2026, 9, 13)

_EMPTY_PLAN = {"planned": [], "held_back": [], "hr_list": []}
_CLEAN_CONFIG = {"shifts": [], "issues": [], "count": 0}


def _report(sections, from_date="2026-09-13", to_date="2026-09-13"):
	return {"from_date": from_date, "to_date": to_date, "sections": sections}


def _section(fix="assignments", count=0, sample=None):
	return {"fix": fix, "count": count, "sample": sample or [], "days": 0, "held_back": 0, "hr_list": 0}


class _Base(unittest.TestCase):
	def setUp(self):
		self.patches = [
			patch.object(health, "now_datetime", return_value=TODAY),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "log_error", MagicMock(), create=True),
			patch.object(frappe, "get_traceback", MagicMock(return_value="tb"), create=True),
			patch.object(frappe, "only_for", MagicMock(), create=True),
			patch.object(frappe, "get_roles", lambda *a: ["HR Manager"], create=True),
			patch.object(health, "require_unfenced", MagicMock()),
			# S1: the config-health block is a separate read; clean unless a test says otherwise.
			patch.object(health.rec, "config_health", return_value=_CLEAN_CONFIG),
		]
		for p in self.patches:
			p.start()
		frappe.db.exists.return_value = False

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()


# --- pure helpers -----------------------------------------------------------------


class TestBrokenSections(unittest.TestCase):
	def test_a_zero_count_section_is_not_broken(self):
		self.assertEqual(health._broken({"x": _section(count=0)}), {})

	def test_a_nonzero_count_section_is_broken(self):
		broken = health._broken({"x": _section(count=3)})
		self.assertEqual(set(broken), {"x"})

	def test_a_section_with_no_fix_is_never_broken_even_with_a_count(self):
		# h_days_after_today shape: informational, never a fix.
		self.assertEqual(health._broken({"h": {"fix": None, "count": 5}}), {})

	def test_an_unreadable_section_counts_as_broken_even_without_a_count_key(self):
		broken = health._broken({"x": {"error": "boom"}})
		self.assertEqual(set(broken), {"x"})

	def test_a_section_that_is_100_percent_held_is_listed_not_hidden(self):
		# R5 (15 Sep 2026): Ria's wrong night assignment was held for HR every night
		# and never reached the log, because count was 0.
		held_only = {**_section(fix="assignments", count=0), "held_back": 3, "count_needs_hr": 3}
		self.assertEqual(set(health._broken({"a": held_only})), {"a"})

	def test_a_detector_section_without_a_step_is_judged_by_its_family(self):
		lone_in = {"fix": None, "family": "F2", "count": 0, "held_back": 2, "count_needs_hr": 2}
		self.assertEqual(set(health._broken({"l_lone_in": lone_in})), {"l_lone_in"})
		clean = {"fix": None, "family": "F2", "count": 0, "held_back": 0}
		self.assertEqual(health._broken({"l_lone_in": clean}), {})

	def test_count_adds_the_days_only_hr_can_fix(self):
		self.assertEqual(health._count({**_section(count=2), "count_needs_hr": 3, "count_on_purpose": 9}), 5)

	def test_lines_show_the_hold_split_and_each_held_reason(self):
		section = {
			**_section(fix="assignments", count=0),
			"held_back": 2,
			"count_needs_hr": 1,
			"count_on_purpose": 1,
			"hr_sample": [{"employee": "E9", "date": "2026-09-13", "reason": "future range — HR to end"}],
		}
		lines = health._lines("a_wrong_night_assignment", section)
		self.assertIn("held back: 1 need HR, 1 left alone on purpose", lines[0])
		self.assertIn("E9 2026-09-13: HELD — future range — HR to end", lines[1])

	def test_count_treats_an_error_as_one(self):
		self.assertEqual(health._count({"error": "boom"}), 1)
		self.assertEqual(health._count(_section(count=4)), 4)

	def test_lines_names_the_recovery_step_and_up_to_10_samples(self):
		sample = [{"employee": f"E{i}", "date": "2026-09-13"} for i in range(15)]
		lines = health._lines(
			"a_wrong_night_assignment", _section(fix="assignments", count=15, sample=sample)
		)
		self.assertIn("recovery step: assignments", lines[0])
		self.assertEqual(len(lines) - 1, 10)
		self.assertIn("E0 2026-09-13", lines[1])


# --- run_daily_health_check ---------------------------------------------------------


class TestRunDailyHealthCheck(_Base):
	def test_no_error_log_when_all_zero(self):
		clean = {"a_wrong_night_assignment": _section(count=0)}
		with patch.object(health.rec, "inputs_report", return_value=_report(clean)):
			health.run_daily_health_check()
		frappe.log_error.assert_not_called()

	def test_one_error_log_with_the_right_title_when_counts_exist(self):
		broken = {
			"a_wrong_night_assignment": _section(
				fix="assignments", count=2, sample=[{"employee": "E1", "date": "2026-09-13"}]
			),
			"h_days_after_today": {"fix": None, "count": 5},
		}
		with patch.object(health.rec, "inputs_report", side_effect=[_report(broken), _report({})]):
			health.run_daily_health_check()
		frappe.log_error.assert_called_once()
		title = frappe.log_error.call_args.kwargs["title"]
		self.assertEqual(title, f"Attendance health: 2 broken day(s) on {YESTERDAY}")
		message = frappe.log_error.call_args.kwargs["message"]
		self.assertIn("E1", message)
		self.assertIn("assignments", message)
		self.assertNotIn("h_days_after_today", message)

	def test_no_duplicate_on_a_second_run_the_same_day(self):
		broken = {"a_wrong_night_assignment": _section(count=1, sample=[{"employee": "E1", "date": "x"}])}
		frappe.db.exists.return_value = True
		with patch.object(health.rec, "inputs_report", return_value=_report(broken)):
			health.run_daily_health_check()
		frappe.log_error.assert_not_called()
		frappe.db.exists.assert_called_with(
			"Error Log", {"method": f"Attendance health: 1 broken day(s) on {YESTERDAY}"}
		)

	def test_exceptions_are_swallowed_and_logged(self):
		with patch.object(health.rec, "inputs_report", side_effect=RuntimeError("boom")):
			health.run_daily_health_check()  # must not raise
		frappe.log_error.assert_called_once_with(title=health.FAILURE_TITLE, message="tb")

	def test_a_failing_log_error_call_is_also_swallowed(self):
		frappe.log_error.side_effect = RuntimeError("log store is down")
		with patch.object(health.rec, "inputs_report", side_effect=RuntimeError("boom")):
			health.run_daily_health_check()  # still must not raise

	def test_config_issues_reach_the_log_even_when_no_day_is_broken(self):
		issue = {"scope": "shift", "name": "9AM-6PM", "issue": "buffers 360/360 min exceed 120"}
		with (
			patch.object(health.rec, "inputs_report", return_value=_report({})),
			patch.object(
				health.rec, "config_health", return_value={"shifts": [], "issues": [issue], "count": 1}
			),
		):
			health.run_daily_health_check()
		frappe.log_error.assert_called_once()
		self.assertEqual(
			frappe.log_error.call_args.kwargs["title"], f"Attendance health: 1 config issue(s) on {YESTERDAY}"
		)
		message = frappe.log_error.call_args.kwargs["message"]
		self.assertIn("Config health (report only, shift config is HR's): 1 issue(s)", message)
		self.assertIn("shift 9AM-6PM: buffers 360/360 min exceed 120", message)

	def test_a_crashing_config_read_is_reported_in_the_body_not_raised(self):
		with (
			patch.object(health.rec, "inputs_report", return_value=_report({})),
			patch.object(health.rec, "config_health", side_effect=RuntimeError("boom")),
		):
			health.run_daily_health_check()
		frappe.log_error.assert_called_once()
		self.assertIn("Config health: could not be read (boom)", frappe.log_error.call_args.kwargs["message"])

	def test_never_queries_today(self):
		with patch.object(health.rec, "inputs_report", return_value=_report({})) as reads:
			health.run_daily_health_check()
		self.assertEqual(reads.call_count, 2)
		for call in reads.call_args_list:
			self.assertLessEqual(call.kwargs["to_date"], str(YESTERDAY))
			self.assertLessEqual(call.kwargs["from_date"], str(YESTERDAY))
			self.assertEqual(call.kwargs["include_source"], 0)
		# one call for yesterday alone, one for the rolling week ending yesterday
		to_dates = {call.kwargs["to_date"] for call in reads.call_args_list}
		self.assertEqual(to_dates, {str(YESTERDAY)})
		from_dates = sorted(call.kwargs["from_date"] for call in reads.call_args_list)
		self.assertEqual(from_dates, [str(date(2026, 9, 7)), str(YESTERDAY)])


_BROKEN_ONE = {"a_wrong_night_assignment": _section(count=1, sample=[{"employee": "E1", "date": "x"}])}


class TestHrSeesTheAlert(_Base):
	"""Group 2-4 review W6: Error Log is System Manager only, so the daily alert
	never reached HR. Each HR Manager / HR User who may see every company gets a
	Desk Notification Log linked to the Error Log, once, like the log itself."""

	def _run(self, fenced=(), fail_insert=False):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		inserted = []

		def get_all(doctype, filters=None, pluck=None, **kw):
			if doctype == "Has Role":
				return ["hr.manager@x", "hr.user@x", "hr.user@x"]
			if doctype == "User":
				return ["hr.manager@x", "hr.user@x"]
			return []

		def get_doc(values, *a, **kw):
			doc = MagicMock()

			def insert(**kwargs):
				if fail_insert:
					raise RuntimeError("notification store is down")
				inserted.append(values)

			doc.insert.side_effect = insert
			return doc

		frappe.log_error.return_value = MagicMock()
		frappe.log_error.return_value.name = "ERR-0001"
		with (
			patch.object(health.rec, "inputs_report", return_value=_report(_BROKEN_ONE)),
			patch.object(frappe, "get_all", side_effect=get_all, create=True),
			patch.object(frappe, "get_doc", side_effect=get_doc, create=True),
			patch.object(hooks, "company_visible", lambda company, user: user not in fenced, create=True),
		):
			health.run_daily_health_check()
		return inserted

	def test_each_unfenced_hr_user_gets_one_desk_alert_linked_to_the_error_log(self):
		inserted = self._run()
		self.assertEqual(sorted(n["for_user"] for n in inserted), ["hr.manager@x", "hr.user@x"])
		for note in inserted:
			self.assertEqual(note["doctype"], "Notification Log")
			self.assertEqual(note["type"], "Alert")
			self.assertEqual((note["document_type"], note["document_name"]), ("Error Log", "ERR-0001"))
			self.assertEqual(note["subject"], f"Attendance health: 1 broken day(s) on {YESTERDAY}")
			self.assertIn("E1", note["email_content"])

	def test_a_company_fenced_hr_user_does_not_get_the_hub_wide_alert(self):
		inserted = self._run(fenced=("hr.user@x",))
		self.assertEqual([n["for_user"] for n in inserted], ["hr.manager@x"])

	def test_an_already_logged_day_sends_no_second_alert(self):
		frappe.db.exists.return_value = True
		self.assertEqual(self._run(), [])

	def test_a_failing_notification_never_raises_and_keeps_the_error_log(self):
		self.assertEqual(self._run(fail_insert=True), [])
		frappe.log_error.assert_called_once()
		self.assertTrue(frappe.log_error.call_args.kwargs["title"].startswith("Attendance health: 1"))


# --- health_summary -------------------------------------------------------------------


class TestHealthSummary(_Base):
	def _patched_planners(self):
		# Every planner `_sections` reads: the six fix-bearing ones and the S1 detectors.
		return tuple(
			patch.object(health.rec, planner, return_value=_EMPTY_PLAN)
			for _name, _fix, planner, _family in health._SECTION_STEPS
		)

	def test_checks_the_role_tuple_and_the_company_fence(self):
		with self._context(self._patched_planners()):
			health.health_summary()
		frappe.only_for.assert_called_once_with(("System Manager", "HR Manager", "HR User"))
		health.require_unfenced.assert_called_once()

	def test_returns_the_fix_bearing_and_detector_sections_for_both_windows(self):
		with self._context(self._patched_planners()):
			result = health.health_summary(days=7)
		self.assertEqual(result["date"], str(YESTERDAY))
		expected = {
			"a_wrong_night_assignment",
			"b_shiftless_punches",
			"c_skip_stamped_punches",
			"d_mirrored_absent_rows",
			"e_late_checkout_still_broken",
			"g_overwritten_punches",
			# S1 detectors (attendance_recovery.UNCLAIMABLE_FAMILIES)
			"k_wrong_shift_taps",
			"l_lone_in",
			"m_out_first_or_double_out",
			"n_no_attendance_row",
			"o_skipped_taps",
			"p_late_checkout_requests",
			"q_present_without_live_taps",
		}
		self.assertEqual(set(result["daily"]["sections"]), expected)
		self.assertEqual(set(result["trend"]["sections"]), expected)
		self.assertEqual(result["config"], _CLEAN_CONFIG)
		for section in result["trend"]["sections"].values():
			self.assertEqual(section["count"] + section["count_on_purpose"] + section["count_needs_hr"], 0)
		self.assertEqual(result["daily"]["from_date"], str(YESTERDAY))
		self.assertEqual(result["trend"]["from_date"], str(date(2026, 9, 7)))

	def test_days_are_clamped_to_1_through_62_instead_of_raising(self):
		with self._context(self._patched_planners()):
			wide = health.health_summary(days=500)
			narrow = health.health_summary(days=-3)
		# 62 days back from 13 Sep reaches before the repair floor, which clamps it
		self.assertEqual(wide["trend"]["from_date"], "2026-08-01")
		self.assertEqual(narrow["trend"]["from_date"], str(YESTERDAY))

	def test_a_section_that_raises_is_reported_not_crashed(self):
		patches = list(self._patched_planners())
		patches[0] = patch.object(health.rec, "_plan_assignments", side_effect=RuntimeError("boom"))
		with self._context(patches):
			result = health.health_summary()
		self.assertIn("error", result["daily"]["sections"]["a_wrong_night_assignment"])

	def _context(self, patches):
		from contextlib import ExitStack

		stack = ExitStack()
		for p in patches:
			stack.enter_context(p)
		return stack


# --- scheduler wiring -----------------------------------------------------------------


HOOKS_PATH = pathlib.Path(__file__).resolve().parents[1] / "hooks.py"

#: Frozen at the base commit named for this slice (d3392681e), read straight out
#: of hooks.py at that point in history. If a future rebase changes the base
#: scheduler_events block for real reasons, refresh this literal to match —
#: it exists to catch an ACCIDENTAL drop from THIS change, not to freeze the
#: block forever.
BASE_SCHEDULER_EVENTS = {
	"all": [
		"hrms.hr.doctype.interview.interview.send_interview_reminder",
	],
	"hourly": [
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails",
	],
	"hourly_long": [
		"hrms.hr.doctype.shift_type.shift_type.update_last_sync_of_checkin",
		"hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
		"hrms.hr.doctype.shift_schedule_assignment.shift_schedule_assignment.process_auto_shift_creation",
	],
	"daily": [
		"hrms.hr.shift_rules.sync_shift_assignments",
		"hrms.hr.leave_rules.auto_assign_leave_policies",
		"hrms.overrides.employee_master.update_all_years_of_service",
		"hrms.controllers.employee_reminders.send_birthday_reminders",
		"hrms.controllers.employee_reminders.send_work_anniversary_reminders",
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"hrms.hr.doctype.interview.interview.send_daily_feedback_reminder",
		"hrms.hr.doctype.shift_assignment.shift_assignment.mark_expired_shift_assignments_as_inactive",
		"hrms.hr.doctype.job_opening.job_opening.close_expired_job_openings",
		"hrms.telemetry.capture_daily_attendance_pulse",
		"hrms.utils.company_fence.nightly_fence_hygiene",
		"hrms.sync.health.report_stale_instances",
		"hrms.utils.readiness.report_readiness",
		"hrms.hr.offboarding.update_relieved_employee_status",
	],
	"cron": {
		"0 10 * * *": [
			"hrms.utils.checkin_sweeper.sweep_stale_ins",
		],
	},
	"daily_long": [
		"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
		"hrms.hr.utils.generate_leave_encashment",
		"hrms.hr.utils.allocate_earned_leaves",
	],
	"weekly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_weekly"],
	"monthly": [
		"hrms.controllers.employee_reminders.send_reminders_in_advance_monthly",
		"hrms.hr.doctype.attendance_allowance_type.attendance_allowance_type.process_attendance_allowances",
	],
}

NEW_ENTRY = "hrms.utils.attendance_health.run_daily_health_check"


def _scheduler_events_from_source(source: str) -> dict:
	tree = ast.parse(source)
	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == "scheduler_events" for t in node.targets
		):
			return ast.literal_eval(node.value)
	raise AssertionError("scheduler_events assignment not found in hooks.py")


def _flatten(events: dict) -> set:
	jobs = set()
	for bucket, entries in events.items():
		if bucket == "cron":
			for jobs_for_cron in entries.values():
				jobs.update(jobs_for_cron)
		else:
			jobs.update(entries)
	return jobs


class TestSchedulerEntry(unittest.TestCase):
	def test_hooks_py_still_parses_as_a_plain_literal(self):
		current = _scheduler_events_from_source(HOOKS_PATH.read_text(encoding="utf-8"))
		self.assertIn("daily", current)

	def test_every_base_entry_survives_and_exactly_one_is_added(self):
		current = _scheduler_events_from_source(HOOKS_PATH.read_text(encoding="utf-8"))
		for bucket, base_entries in BASE_SCHEDULER_EVENTS.items():
			self.assertIn(bucket, current, f"bucket {bucket!r} was dropped")
			if bucket == "cron":
				for cron_expr, jobs in base_entries.items():
					self.assertEqual(
						current[bucket].get(cron_expr), jobs, f"cron entry {cron_expr!r} changed"
					)
			else:
				for job in base_entries:
					self.assertIn(job, current[bucket], f"{job!r} was dropped from {bucket!r}")
		added = _flatten(current) - _flatten(BASE_SCHEDULER_EVENTS)
		# attendance_auto_recovery.run_nightly joined the daily list later (Nabil, 14 Sep 2026).
		self.assertEqual(added, {NEW_ENTRY, "hrms.utils.attendance_auto_recovery.run_nightly"})

	def test_the_new_entry_is_a_daily_job(self):
		current = _scheduler_events_from_source(HOOKS_PATH.read_text(encoding="utf-8"))
		self.assertIn(NEW_ENTRY, current.get("daily", []))


if __name__ == "__main__":
	unittest.main()
