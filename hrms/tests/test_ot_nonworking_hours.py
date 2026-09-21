"""Holiday worked minutes survive every OT consumer and weekday cap accounting."""

import ast
import importlib
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, time, timedelta
from itertools import groupby
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
ot = importlib.import_module("hrms.utils.ot_calculation")
filing = importlib.import_module("test_ot_filing_edits")
frappe = filing.frappe
API = importlib.import_module("test_ot_claim_monthly_capacity").API
DAY = date(2026, 9, 6)


def punch(day, value, log_type, **extra):
	return frappe._dict(
		employee="EMP-SYNTHETIC",
		time=datetime.combine(day, time.fromisoformat(value)),
		log_type=log_type,
		shift="SHIFT-SYNTHETIC",
		shift_start=datetime.combine(day, time(9)),
		shift_end=datetime.combine(day, time(18)),
		shift_actual_start=datetime.combine(day, time(8)),
		shift_actual_end=datetime.combine(day, time(23)),
		remote_approval_status="Approved",
		**extra,
	)


# Execute native source methods; persistence and unrelated holiday half-day
# metadata are boundaries. No copied attendance algorithm or threshold mock.
BASE = Path(__file__).resolve().parents[1]
shift_tree = ast.parse((BASE / "hr/doctype/shift_type/shift_type.py").read_text())
shift_class = next(
	node for node in shift_tree.body if isinstance(node, ast.ClassDef) and node.name == "ShiftType"
)
shift_class.bases = []
shift_class.body = [
	node
	for node in shift_class.body
	if isinstance(node, ast.FunctionDef)
	and node.name
	in {
		"get_attendance",
		"get_employee_checkins",
		"_deduct_unpaid_breaks",
		"should_mark_attendance",
		"get_holiday_list",
		"is_half_holiday",
		"mark_attendance_for_shift_logs",
		# mark_attendance_for_shift_logs reads the day through this since the
		# read/write split (51902996c); the rule under test lives here.
		"shift_day_result",
	}
]
# Module-level helpers the class body calls by name. `counts_for_attendance` is
# the attendance evidence rule (a pending punch counts; rejected/off-shift/skipped
# do not) — wider than overtime's `_is_eligible_checkin` on purpose.
# `paid_intervals_from` trims an early arrival off the paid hours.
# `attendance_segments`/`splits_the_day` cut the day into spans: a tap somebody
# ignored is dropped, a rejected/off-shift/unapproved one is a wall (17 Sep 2026).
shift_helpers = [
	node
	for node in shift_tree.body
	if (
		isinstance(node, ast.FunctionDef)
		and node.name
		in {
			"counts_for_attendance",
			"paid_intervals_from",
			"attendance_segments",
			"_cut_overlong_sessions",
			"splits_the_day",
			# the field list is asked for at read time: a site without the
			# `skipped_as_noise` column must not have it named in the SELECT
			"checkin_fields",
			# the one loader every reader shares (21 Sep 2026)
			"day_evidence",
			"pending_late_checkouts",
		}
	)
	or (
		isinstance(node, ast.Assign)
		and any(isinstance(t, ast.Name) and t.id in {"CHECKIN_FIELDS", "NOISE_FIELD"} for t in node.targets)
	)
]
checkin_tree = ast.parse((BASE / "hr/doctype/employee_checkin/employee_checkin.py").read_text())
calcs = [
	node
	for node in checkin_tree.body
	if isinstance(node, ast.FunctionDef)
	and node.name
	in {"calculate_working_hours", "worked_intervals", "time_diff_in_hours", "find_index_in_dict"}
]
SHIFT = {
	"frappe": frappe,
	"flt": float,
	"cint": int,
	"get_datetime": ot.get_datetime,
	"getdate": ot.getdate,
	"timedelta": timedelta,
	"SESSION_WINDOW": timedelta(hours=20),
	"groupby": groupby,
	"logger": __import__("logging").getLogger(__name__),
	"_company_of_logs": lambda logs: "COMPANY-SYNTHETIC",
	"get_holiday_list_for_employee": lambda *args, **kwargs: "HOLIDAYS-SYNTHETIC",
	"is_holiday": lambda *args: True,
	"holiday_list_covers": lambda *args: True,
	"is_half_holiday": lambda *args: False,
	"mark_attendance_and_link_log": Mock(),
	# A day already marked is rebuilt from all its punches (9 Sep). These
	# scenarios start from an unmarked day, so the lookup finds nothing.
	"get_automation_attendance": lambda *args, **kwargs: None,
	"linked_checkins": lambda *args, **kwargs: [],
	# no day in these scenarios was removed by HR in Shift Attendance
	"removed_by_hr": lambda *args, **kwargs: False,
	"hold_punches": Mock(),
}
exec(
	compile(
		ast.Module(body=[*calcs, *shift_helpers, shift_class], type_ignores=[]),
		str(BASE / "hr/doctype/shift_type/shift_type.py"),
		"exec",
	),
	SHIFT,
)


class TestNonworkingHours(unittest.TestCase):
	def context(self, *, rows=None, holidays=None, approved=(), cap=1, minimum=60, policy=None):
		rows = rows if rows is not None else [punch(DAY, "10:08", "IN"), punch(DAY, "13:22", "OUT")]
		holidays = {DAY: 1} if holidays is None else holidays
		shift = frappe._dict(
			enable_overtime=1,
			minimum_overtime_minutes=minimum,
			overtime_working_days_per_month=26,
			overtime_normal_hours_per_day=8,
			daily_overtime_cap_hours=cap,
			monthly_overtime_cap_hours=cap,
			start_time=time(9),
			end_time=time(18),
			allow_check_out_after_shift_end_time=300,
			determine_check_in_and_check_out=policy or "Strictly based on Log Type in Employee Checkin",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			overtime_rates=[
				frappe._dict(
					day_type=label, from_hour=start, from_minute=0, to_hour=end, to_minute=0, rate=rate
				)
				for label, start, end, rate in (
					("Normal Day", 0, 24, 1.5),
					("Rest Day", 0, 24, 2),
					("Off Day", 0, 24, 1.5),
					("Public Holiday", 0, 8, 2),
					("Public Holiday", 8, 24, 3),
				)
			],
			breaks=[
				frappe._dict(
					day_of_week="Sunday",
					period="Normal only",
					break_type="Fixed",
					start_time=time(12),
					end_time=time(13),
				)
			],
		)

		def get_all(doctype, filters=None, **kwargs):
			if doctype == "Employee Checkin":
				start, end = filters["time"][1]
				return [
					row
					for row in rows
					if ot.get_datetime(start) <= row.time <= ot.get_datetime(end)
					and (not filters.get("shift") or row.shift == filters["shift"])
				]
			if doctype == "Attendance":
				return [
					frappe._dict(attendance_date=day, ot_hours=0)
					for day in sorted({row.time.date() for row in rows})
				]
			if doctype == "OT Request":
				if kwargs.get("pluck"):
					return [day for day, _ in approved]
				return [
					frappe._dict(ot_date=day, claimed_hours=hours, shift="SHIFT-SYNTHETIC")
					for day, hours in approved
				]
			raise AssertionError(doctype)

		def get_value(doctype, name, field, **kwargs):
			if doctype == "Shift Type":
				return "HOLIDAYS-SYNTHETIC" if field == "holiday_list" else shift.get(field)
			if doctype == "Attendance":
				return "SHIFT-SYNTHETIC"
			if doctype == "Employee":
				return 1 if field == "eligible_for_overtime_pay" else "COMPANY-SYNTHETIC"
			if doctype == "Company":
				return ("Sunday", "Saturday")
			if doctype == "Holiday":
				weekly_off = holidays.get(name["holiday_date"])
				return None if weekly_off is None else frappe._dict(weekly_off=weekly_off)
			if doctype == "Holiday List":  # the synthetic calendar covers every test date
				return (date(2025, 1, 1), date(2027, 12, 31))
			raise AssertionError(doctype)

		stack = ExitStack()
		stack.enter_context(patch.object(frappe, "get_all", side_effect=get_all))
		stack.enter_context(patch.object(frappe.db, "get_value", side_effect=get_value))
		stack.enter_context(patch.object(frappe.db, "exists", return_value=False))
		# Locking reads answer from the same synthetic rows as the snapshot reads.
		stack.enter_context(
			patch.object(
				frappe.db,
				"get_values",
				side_effect=lambda doctype, filters=None, fields=None, **kwargs: (
					[] if fields == "name" else get_all(doctype, filters=filters, fields=fields)
				),
			)
		)
		stack.enter_context(patch.object(frappe, "get_cached_doc", return_value=shift))
		stack.enter_context(
			patch.dict(
				sys.modules,
				{
					"erpnext.setup.doctype.employee.employee": SimpleNamespace(
						get_holiday_list_for_employee=lambda *args, **kwargs: "HOLIDAYS-SYNTHETIC"
					)
				},
			)
		)
		return stack

	def shift(self):
		shift = SHIFT["ShiftType"]()
		shift.__dict__.update(
			name="SHIFT-SYNTHETIC",
			holiday_list="HOLIDAYS-SYNTHETIC",
			mark_auto_attendance_on_holidays=0,
			determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
			working_hours_calculation_based_on="First Check-in and Last Check-out",
			breaks=[{}],
			enable_late_entry_marking=1,
			enable_early_exit_marking=1,
			late_entry_grace_period=0,
			early_exit_grace_period=0,
			working_hours_threshold_for_absent=4,
			working_hours_threshold_for_half_day=8,
		)
		return shift

	def test_nonworking_attendance_is_present_exact_and_has_no_weekday_flags(self):
		rows = [punch(DAY, "10:08", "IN"), punch(DAY, "13:22", "OUT")]
		shift = self.shift()
		with (
			self.context(rows=rows),
			patch.object(shift, "_deduct_unpaid_breaks", return_value=1) as deduction,
		):
			result = shift.get_attendance(rows, 4, 8)
			self.assertEqual(result[0], "Present")
			self.assertAlmostEqual(result[1], 194 / 60)
			self.assertEqual(result[2:4], (False, False))
			deduction.assert_not_called()

	def test_actual_holiday_work_is_marked_despite_checkbox_and_repair_forwarding_stays(self):
		rows = [punch(DAY, "10:08", "IN"), punch(DAY, "13:22", "OUT")]
		shift = self.shift()
		marker = SHIFT["mark_attendance_and_link_log"]
		marker.reset_mock()
		repair = object()
		with self.context(rows=rows):
			shift.mark_attendance_for_shift_logs("EMP-SYNTHETIC", DAY, rows, repair_attendance=repair)
		marker.assert_called_once()
		self.assertEqual(marker.call_args.args[1], "Present")
		self.assertIs(marker.call_args.kwargs["repair_attendance"], repair)

	def test_incomplete_holiday_pair_creates_no_attendance_or_auto_absence(self):
		rows = [punch(DAY, "10:08", "IN")]
		shift = self.shift()
		marker = SHIFT["mark_attendance_and_link_log"]
		marker.reset_mock()
		with self.context(rows=rows):
			self.assertIsNone(shift.mark_attendance_for_shift_logs("EMP-SYNTHETIC", DAY, rows))
		marker.assert_not_called()

	def test_scheduler_retains_invalid_boundary_and_links_only_eligible_logs(self):
		# A PENDING punch is deliberately absent from this list since 9 Sep: it is
		# provisional presence for attendance (see test_pending_punch_attendance)
		# while staying out of overtime pairing. Treating it as invalid here
		# auto-marked every out-of-radius employee Absent on the live site.
		for invalid in (
			{"skip_auto_attendance": 1},
			{"remote_approval_status": "Rejected"},
			{"offshift": 1},
		):
			with self.subTest(invalid=invalid):
				rows = [
					punch(DAY, value, kind)
					for value, kind in [("09:00", "IN"), ("10:00", "OUT"), ("12:00", "OUT")]
				]
				rows[1].update(invalid)
				for index, row in enumerate(rows):
					row.name = f"PUNCH-SYNTHETIC-{index}"
				shift = self.shift()
				shift.process_attendance_after = str(DAY)
				shift.last_sync_of_checkin = str(DAY + timedelta(days=1))

				def query(doctype, fields, filters, **kwargs):
					# Honor actual query exclusion and field projection, not just
					# return the full fixture and hide the scheduler boundary.
					return [
						frappe._dict({key: row.get(key) for key in fields})
						for row in rows
						if all(
							row.get(key, 0) == value
							for key, value in filters.items()
							if key in {"skip_auto_attendance", "offshift"}
						)
					]

				marker = SHIFT["mark_attendance_and_link_log"]
				marker.reset_mock()
				with self.context(rows=rows), patch.object(frappe, "get_all", side_effect=query):
					fetched = shift.get_employee_checkins()
					self.assertIsNone(shift.mark_attendance_for_shift_logs("EMP-SYNTHETIC", DAY, fetched))
					marker.assert_not_called()
					# A later complete pair remains usable. Invalid evidence is
					# retained for calculation but must not be linked/claimed.
					rows.extend(
						[
							punch(DAY, "13:00", "IN", name="PUNCH-SYNTHETIC-3"),
							punch(DAY, "14:00", "OUT", name="PUNCH-SYNTHETIC-4"),
						]
					)
					shift.mark_attendance_for_shift_logs("EMP-SYNTHETIC", DAY, shift.get_employee_checkins())
					self.assertEqual(marker.call_args.args[3], 1)
					self.assertNotIn("PUNCH-SYNTHETIC-1", [row.name for row in marker.call_args.args[0]])

	def boundary_hours(self, **boundary):
		rows = [
			punch(DAY, value, kind)
			for value, kind in [
				("09:00", "IN"),
				("10:00", "OUT"),
				("12:00", "OUT"),
				("13:00", "IN"),
				("19:00", "OUT"),
			]
		]
		for field, value in boundary.items():
			setattr(rows[1], field, value)
		shift = self.shift()
		shift.breaks = []
		with self.context(rows=rows, holidays={}):
			return shift.get_attendance(rows, 4, 8)[1]

	def test_weekday_invalid_boundary_does_not_bridge_native_first_last_policy(self):
		"""A REJECTED punch is still a wall: 13:00-19:00 only, never 09:00-19:00.

		Amended 17 Sep 2026. This drove the boundary with a bare
		`skip_auto_attendance = 1`, which is now the OTHER case — see below. The
		rule the test is named for is about evidence nobody verified, and
		rejection is what makes a punch that; it is asserted with a rejection now.
		"""
		self.assertEqual(self.boundary_hours(skip_auto_attendance=1, remote_approval_status="Rejected"), 6)

	def test_an_off_shift_boundary_does_not_bridge_either(self):
		self.assertEqual(self.boundary_hours(offshift=1), 6)

	def test_a_tap_the_system_deferred_is_still_a_wall(self):
		"""Skipped without a verdict — `handle_attendance_exception` gave up on
		the batch when the financial guard refused the rebuild. Nobody judged
		that punch, so the day is still not read across it."""
		self.assertEqual(self.boundary_hours(skip_auto_attendance=1), 6)

	def test_a_tap_somebody_ignored_is_removed_and_the_day_is_one_span(self):
		"""Owner ruling, 17 Sep 2026: "the 11 am out is possible accidental and
		should be fine for us to fix by removing it alongside the broken glitch
		stuff. applicable to any scenarios."

		So a plain skipped tap is not a wall — it is not there at all, and the
		day runs 09:00 to 19:00. Live proof of the old reading: Norazlin's
		4 September, where HR ignored the accidental mid-day OUT and the glitch
		burst and the day came back "in 09:03 · out — · 0 h worked", because the
		two real taps had been left in two one-tap spans."""
		self.assertEqual(self.boundary_hours(skip_auto_attendance=1, skipped_as_noise=1), 10)

	def test_rest_day_all_194_minutes_reach_breakdowns_claim_and_payroll(self):
		hours = 194 / 60
		with self.context(approved=[(DAY, hours)]):
			self.assertAlmostEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], hours)
			self.assertAlmostEqual(
				ot.get_shift_ot_breakdown(
					"EMP-SYNTHETIC",
					"SHIFT-SYNTHETIC",
					DAY,
					datetime.combine(DAY, time(13, 22)),
					in_time=datetime.combine(DAY, time(10, 8)),
				)["ot_hours"],
				hours,
			)
			self.assertAlmostEqual(
				ot.get_ot_claim_capacity("EMP-SYNTHETIC", DAY, "Overtime Pay")["hours"], hours
			)
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", DAY, DAY, 2080), 64.67)
			doc = filing.ot_request.OTRequest(
				dict(
					name="OT-SYNTHETIC",
					employee="EMP-SYNTHETIC",
					ot_date=DAY,
					amended_from=None,
					_new=True,
					_previous=None,
					shift="SHIFT-SYNTHETIC",
					claimed_hours=hours,
					status="Open",
				)
			)
			with patch.object(
				filing.ot_request,
				"getdate",
				side_effect=lambda value=None: (
					date(2026, 9, 30) if value is None else date.fromisoformat(str(value))
				),
			):
				doc.validate()
			self.assertAlmostEqual(doc.punch_ot_hours, hours)

	def test_public_holiday_nine_hours_use_existing_eight_at_two_one_at_three_bands(self):
		rows = [punch(DAY, "09:00", "IN"), punch(DAY, "18:00", "OUT")]
		with self.context(rows=rows, holidays={DAY: 0}, approved=[(DAY, 9)]):
			result = ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)
			self.assertEqual(result["ot_hours"], 9)
			self.assertEqual([(row["hours"], row["rate"]) for row in result["bands"]], [(8, 2), (1, 3)])
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", DAY, DAY, 2080), 190)

	def test_nonworking_claims_do_not_spend_or_displace_weekday_cap(self):
		weekday = date(2026, 9, 7)
		rows = [
			punch(DAY, "10:08", "IN"),
			punch(DAY, "13:22", "OUT"),
			punch(weekday, "09:00", "IN"),
			punch(weekday, "19:00", "OUT"),
		]
		with self.context(rows=rows, approved=[(DAY, 194 / 60), (weekday, 1)]):
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", weekday, weekday, 2080), 15)
			self.assertAlmostEqual(
				ot.get_ot_claim_capacity("EMP-SYNTHETIC", DAY, "Overtime Pay")["hours"], 194 / 60
			)
		with self.context(rows=rows, approved=[(DAY, 194 / 60)]):
			self.assertEqual(ot.get_ot_claim_capacity("EMP-SYNTHETIC", weekday, "Overtime Pay")["hours"], 1)

	def test_discovery_adds_holiday_entitlement_without_using_weekday_budget(self):
		weekday = date(2026, 9, 7)
		rows = [
			punch(DAY, "10:08", "IN"),
			punch(DAY, "13:22", "OUT"),
			punch(weekday, "09:00", "IN"),
			punch(weekday, "19:00", "OUT"),
		]
		with self.context(rows=rows):
			self.assertAlmostEqual(
				API["get_ot_claim_summary"]("EMP-SYNTHETIC", str(DAY))["punch_ot_hours"], 194 / 60
			)
			self.assertAlmostEqual(
				API["get_claimable_ot_summary"]("EMP-SYNTHETIC")["claimable_hours"], 194 / 60 + 1
			)

	def test_split_weekday_sessions_do_not_restart_the_shift_lateness_clock(self):
		rows = [
			punch(DAY, "09:00", "IN"),
			punch(DAY, "12:00", "OUT"),
			punch(DAY, "13:00", "IN"),
			punch(DAY, "19:00", "OUT"),
		]
		with self.context(rows=rows, holidays={}, cap=0):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], 1)
			self.assertEqual(
				ot.get_shift_ot_breakdown(
					"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", DAY, rows[-1].time, in_time=rows[0].time
				)["ot_hours"],
				1,
			)

	def test_explicit_out_in_gap_is_not_worked_and_duplicate_in_keeps_first_in(self):
		rows = [
			punch(DAY, "09:00", "IN"),
			punch(DAY, "09:05", "IN"),
			punch(DAY, "10:00", "OUT"),
			punch(DAY, "11:00", "IN"),
			punch(DAY, "13:00", "OUT"),
		]
		with self.context(rows=rows):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], 3)

	def test_attendance_breakdown_uses_pairs_instead_of_the_first_last_span(self):
		rows = [
			punch(DAY, "09:00", "IN"),
			punch(DAY, "10:00", "OUT"),
			punch(DAY, "11:00", "IN"),
			punch(DAY, "13:00", "OUT"),
		]
		with self.context(rows=rows):
			result = ot.get_shift_ot_breakdown(
				"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", DAY, rows[-1].time, in_time=rows[0].time
			)
			self.assertEqual(result["ot_hours"], 3)

	def test_midnight_does_not_change_the_shift_day_type_in_either_breakdown_path(self):
		# Was 1h: the rest-day hour before midnight, the Monday hour after it
		# re-classified as weekday work and discarded. Owner ruling (14 Sep 2026):
		# the whole session belongs to the rest day it started on.
		rows = [punch(DAY, "23:00", "IN"), punch(DAY, "01:00", "OUT")]
		rows[-1].time += timedelta(days=1)
		with self.context(rows=rows):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], 2)
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY + timedelta(days=1))["ot_hours"], 0)
			result = ot.get_shift_ot_breakdown(
				"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", DAY, rows[-1].time, in_time=rows[0].time
			)
			self.assertEqual(result["ot_hours"], 2)

	def test_alternating_shift_policy_accepts_untyped_punches(self):
		rows = [punch(DAY, "10:08", ""), punch(DAY, "13:22", "")]
		with self.context(rows=rows, policy="Alternating entries as IN and OUT during the same shift"):
			self.assertAlmostEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], 194 / 60)

	def test_pending_and_rejected_evidence_cannot_complete_an_eligible_pair(self):
		for status in ("Pending", "Rejected"):
			rows = [punch(DAY, "09:00", "IN"), punch(DAY, "13:00", "OUT")]
			rows[-1].remote_approval_status = status
			with self.subTest(status=status), self.context(rows=rows):
				self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], 0)

	def test_weekday_post_shift_minimum_is_judged_after_rounding(self):
		"""HR, 10 Sep 2026: "at 50 minutes and above auto rounded to 60m so i am
		eligible for OT Pay." The 60-minute minimum stays; what changed is that
		the 30-minute ladder runs FIRST, so the real boundary sits at 50 minutes.

		Was ("18:59", 0), ("19:00", 1) — 59 minutes was measured raw, failed the
		minimum and was discarded before rounding could carry it to the hour.
		The stored hours stay RAW (0.98); the ladder is applied again when the
		day is claimed, which is what turns it into the payable 1.0.
		"""
		for end, hours in (("18:49", 0), ("18:50", 0.83), ("18:59", 0.98), ("19:00", 1)):
			with (
				self.subTest(end=end),
				self.context(rows=[punch(DAY, "09:00", "IN"), punch(DAY, end, "OUT")], holidays={}, cap=0),
			):
				self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)["ot_hours"], hours)

	@settings(max_examples=50, deadline=None)
	@given(minutes=st.integers(1, 500))
	def test_every_nonworking_minute_survives_weekday_caps_and_rounding(self, minutes):
		start = datetime.combine(DAY, time(9))
		rows = [punch(DAY, "09:00", "IN"), punch(DAY, "09:01", "OUT")]
		rows[-1].time = start + timedelta(minutes=minutes)
		with self.context(rows=rows):
			self.assertAlmostEqual(
				ot.get_ot_claim_capacity("EMP-SYNTHETIC", DAY, "Overtime Pay")["hours"], minutes / 60
			)


WEEKDAY = date(2026, 9, 8)  # a Tuesday; no holiday row unless a test adds one
NEXT_DAY = WEEKDAY + timedelta(days=1)


def _after_midnight(row):
	"""The same punch, one calendar day later — it keeps the shift-day stamps."""
	row.time += timedelta(days=1)
	return row


def _day_shift_out_at_0130(day=WEEKDAY):
	"""A 9-18 shift, IN 09:00, OUT 01:30 the next morning: 7.5h past the end."""
	return [punch(day, "09:00", "IN"), _after_midnight(punch(day, "01:30", "OUT"))]


def _night_shift_out_at_0600(day=WEEKDAY):
	"""A 19:30-03:30 shift, IN 19:30, OUT 06:00 the next morning: 2.5h past the end."""
	rows = [punch(day, "19:30", "IN"), _after_midnight(punch(day, "06:00", "OUT"))]
	for row in rows:
		row.update(
			shift_start=datetime.combine(day, time(19, 30)),
			shift_end=datetime.combine(day + timedelta(days=1), time(3, 30)),
			shift_actual_start=datetime.combine(day, time(18, 30)),
			shift_actual_end=datetime.combine(day + timedelta(days=1), time(8, 30)),
		)
	return rows


class TestOvertimeBelongsToTheShiftDay(unittest.TestCase):
	"""Owner ruling, 14 Sep 2026: overtime belongs to the SHIFT DAY — the date the
	session's shift started — including every minute worked after midnight.

	The slicer used to cut a session at midnight and book each piece to its
	calendar date. A claim is filed for the shift date, so it never saw the
	after-midnight part: all of a night shift's overtime, and the tail of any day
	shift worked past midnight. That is "I can't claim my OT". The same cut
	re-classified the tail by the next day's calendar, so a weekday shift running
	into a public holiday was paid the holiday rate for the last hours of a
	weekday, and a holiday shift running into a weekday lost its holiday rate.
	"""

	def context(self, **kwargs):
		kwargs.setdefault("holidays", {})
		kwargs.setdefault("cap", 0)
		return TestNonworkingHours().context(**kwargs)

	def test_day_shift_worked_past_midnight_books_all_overtime_to_the_shift_date(self):
		rows = _day_shift_out_at_0130()
		with self.context(rows=rows):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", WEEKDAY)["ot_hours"], 7.5)
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", NEXT_DAY)["ot_hours"], 0)
			self.assertEqual(
				ot.get_shift_ot_breakdown(
					"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", WEEKDAY, rows[-1].time, in_time=rows[0].time
				)["ot_hours"],
				7.5,
			)

	def test_night_shift_overtime_lands_on_the_shift_start_date(self):
		rows = _night_shift_out_at_0600()
		with self.context(rows=rows):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", WEEKDAY)["ot_hours"], 2.5)
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", NEXT_DAY)["ot_hours"], 0)
			self.assertEqual(
				ot.get_shift_ot_breakdown(
					"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", WEEKDAY, rows[-1].time, in_time=rows[0].time
				)["ot_hours"],
				2.5,
			)

	def test_weekday_shift_running_into_a_public_holiday_keeps_the_weekday_rate(self):
		for label, rows, hours in (
			("day shift", _day_shift_out_at_0130(), 7.5),
			("night shift", _night_shift_out_at_0600(), 2.5),
		):
			with self.subTest(label), self.context(rows=rows, holidays={NEXT_DAY: 0}):
				result = ot.get_day_ot_breakdown("EMP-SYNTHETIC", WEEKDAY)
				self.assertEqual(result["day_type"], "normal")
				self.assertEqual([(b["hours"], b["rate"]) for b in result["bands"]], [(hours, 1.5)])
				self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", NEXT_DAY)["ot_hours"], 0)

	def test_public_holiday_shift_running_into_a_weekday_keeps_the_holiday_rate(self):
		holiday = WEEKDAY
		rows = [punch(holiday, "09:00", "IN"), _after_midnight(punch(holiday, "01:00", "OUT"))]
		with self.context(rows=rows, holidays={holiday: 0}):
			result = ot.get_day_ot_breakdown("EMP-SYNTHETIC", holiday)
			self.assertEqual(result["day_type"], "public_holiday")
			# 16 worked hours, all holiday work: the fixture's 8h at 2x then 3x bands.
			self.assertEqual([(b["hours"], b["rate"]) for b in result["bands"]], [(8, 2), (8, 3)])
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", NEXT_DAY)["ot_hours"], 0)
			self.assertEqual(
				ot.get_shift_ot_breakdown(
					"EMP-SYNTHETIC", "SHIFT-SYNTHETIC", holiday, rows[-1].time, in_time=rows[0].time
				)["ot_hours"],
				16,
			)

	def test_claim_for_the_shift_date_includes_after_midnight_and_the_next_date_has_none(self):
		for label, rows, hours in (
			("day shift", _day_shift_out_at_0130(), 7.5),
			("night shift", _night_shift_out_at_0600(), 2.5),
		):
			with self.subTest(label), self.context(rows=rows):
				self.assertEqual(
					ot.get_ot_claim_capacity("EMP-SYNTHETIC", WEEKDAY, "Overtime Pay")["hours"], hours
				)
				self.assertEqual(
					ot.get_ot_claim_capacity("EMP-SYNTHETIC", NEXT_DAY, "Overtime Pay")["hours"], 0
				)

	def test_payroll_pays_the_shift_date_claim_once_and_nothing_for_the_next_date(self):
		rows = _night_shift_out_at_0600()
		with self.context(rows=rows, approved=[(WEEKDAY, 2.5), (NEXT_DAY, 2.5)]):
			# 2080 / (26 * 8) = 10/h; 2.5h at 1.5x. The next date's claim prices nothing.
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", WEEKDAY, WEEKDAY, 2080), 37.5)
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", WEEKDAY, NEXT_DAY, 2080), 37.5)

	def test_a_night_shift_on_the_last_day_of_the_month_counts_in_that_month(self):
		last = date(2026, 9, 30)
		rows = _night_shift_out_at_0600(last)
		with self.context(rows=rows, cap=2):
			self.assertEqual(ot.get_ot_claim_capacity("EMP-SYNTHETIC", last, "Overtime Pay")["hours"], 2)
			self.assertEqual(
				ot.get_ot_breakdown("EMP-SYNTHETIC", date(2026, 10, 1), date(2026, 10, 31), 0), {}
			)


if __name__ == "__main__":
	unittest.main()
