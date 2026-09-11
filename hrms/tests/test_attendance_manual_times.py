"""HR can enter and correct in/out times on Attendance in Desk.

Asked for on 9 Sep 2026 while the attendance incident was being repaired:
a person must be able to add an Attendance with its times, and to correct
the times on a submitted row, with the hours recomputed and nothing else
disturbed. Pinned here, bench-free:

  * in_time / out_time are editable, allowed after submit, and always shown;
    the derived fields a correction changes (working hours, overtime) are
    allowed after submit too;
  * a person's times are validated: both or neither, out after in, at most
    24 h apart, in on the attendance date;
  * hours are derived from a person's times only — the hourly job's own rows
    (hours already computed with breaks) are left exactly as computed;
  * a correction after submit recomputes hours and overtime and leaves a
    comment saying what changed.

    PYTHONPATH=. python3 hrms/tests/test_attendance_manual_times.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.attendance import attendance as att

HRMS = pathlib.Path(__file__).resolve().parent.parent
JSON = HRMS / "hr/doctype/attendance/attendance.json"
DAY = date(2026, 9, 8)


def dt(h, m=0, day=DAY):
	return datetime(day.year, day.month, day.day, h, m)


class TestSchema(unittest.TestCase):
	def setUp(self):
		self.fields = {f["fieldname"]: f for f in json.loads(JSON.read_text())["fields"]}

	def test_times_are_editable_after_submit_and_always_shown(self):
		for name in ("in_time", "out_time"):
			with self.subTest(field=name):
				f = self.fields[name]
				self.assertNotEqual(f.get("read_only"), 1)
				self.assertEqual(f.get("allow_on_submit"), 1)
				self.assertFalse(f.get("depends_on"), "a manual row without a shift still needs its times")
				self.assertIn("local", f.get("description", "").lower(), "say whose clock the time is")

	def test_derived_fields_may_change_after_submit(self):
		for name in (
			"working_hours",
			"ot_hours",
			"ot_rate_weighted_hours",
			"ot_rate_bands",
			"late_entry",
			"early_exit",
		):
			with self.subTest(field=name):
				self.assertEqual(self.fields[name].get("allow_on_submit"), 1)

	def test_modified_bumped(self):
		self.assertGreater(json.loads(JSON.read_text())["modified"], "2026-09-09")


class TestTimeRules(unittest.TestCase):
	def test_hours_between(self):
		self.assertEqual(att.working_hours_between(dt(9), dt(18)), 9.0)
		self.assertEqual(att.working_hours_between(dt(9, 30), dt(13)), 3.5)

	def test_a_corrected_day_loses_its_unpaid_break_like_an_automatic_one(self):
		"""The bug Nabil found on his own record, 10 Sep 2026.

		HR-ATT-2026-16073: out time edited by five minutes, working hours went
		from 8.95 to 10.03 — the 1-hour unpaid break stopped being deducted.
		The hourly job deducts it (shift_type._deduct_unpaid_breaks); the typed
		path did not, so every manual correction silently credited the break as
		worked time: +1h Mon-Thu, +1h45m on a Friday, straight into paid hours.

		The raw span stays available (some callers want it); what a correction
		writes must match what the job would have written for the same times.
		"""
		# 9-6 with a one-hour lunch: nine hours in the building, eight paid.
		self.assertEqual(att.working_hours_between(dt(9), dt(18), 60), 8.0)
		# Friday carries the prayer break as well: 1h45m off the same span.
		self.assertEqual(att.working_hours_between(dt(9), dt(18), 105), 7.25)
		# Nabil's day, with his real times.
		self.assertEqual(att.working_hours_between(dt(10, 12), dt(20, 14), 60), 9.03)

	def test_the_raw_span_is_still_what_it_says_with_no_break(self):
		# Unchanged behaviour: no break configured, nothing deducted.
		self.assertEqual(att.working_hours_between(dt(9), dt(18), 0), 9.0)
		self.assertEqual(att.working_hours_between(dt(9), dt(18)), 9.0)

	def test_a_break_longer_than_the_day_cannot_go_negative(self):
		self.assertEqual(att.working_hours_between(dt(9), dt(10), 600), 0.0)

	def test_both_or_neither(self):
		with self.assertRaises(frappe.ValidationError):
			att.validate_attendance_times(dt(9), None, DAY)
		att.validate_attendance_times(None, None, DAY)  # nothing entered is fine

	def test_out_after_in_and_within_a_day(self):
		with self.assertRaises(frappe.ValidationError):
			att.validate_attendance_times(dt(18), dt(9), DAY)
		with self.assertRaises(frappe.ValidationError):
			att.validate_attendance_times(dt(9), dt(10, day=date(2026, 9, 10)), DAY)
		att.validate_attendance_times(dt(22), dt(6, day=date(2026, 9, 9)), DAY)  # night shift, next morning

	def test_in_time_sits_on_the_attendance_date(self):
		with self.assertRaises(frappe.ValidationError):
			att.validate_attendance_times(dt(9, day=date(2026, 9, 7)), dt(18, day=date(2026, 9, 7)), DAY)


class _Doc(SimpleNamespace):
	def __init__(self, **kw):
		defaults = dict(
			name="HR-ATT-1",
			employee="EMP-1",
			attendance_date=DAY,
			status="Present",
			shift="DAY",
			company="_Test Co",
			in_time=None,
			out_time=None,
			working_hours=None,
			auto_attendance=0,
			docstatus=0,
			flags=frappe._dict(),
			comments=[],
			_before=None,
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def get_doc_before_save(self):
		return self._before

	def has_value_changed(self, field):
		if self._before is None:
			return getattr(self, field) is not None
		return getattr(self._before, field, None) != getattr(self, field)

	def add_comment(self, kind=None, text=None, **kw):
		self.comments.append(text)

	def set_overtime(self):
		self.overtime_recomputed = True


class TestAPersonsTimesDeriveTheHours(unittest.TestCase):
	def test_new_manual_row_gets_hours_from_its_times(self):
		doc = _Doc(in_time=dt(9), out_time=dt(18))
		with (
			patch.object(att, "entered_break_minutes", return_value=0),
			patch.object(att, "entered_shift_start", return_value=None),
		):
			att.Attendance.apply_manual_times(doc)
		self.assertEqual(doc.working_hours, 9.0)

	def test_a_new_manual_row_deducts_the_shifts_break(self):
		"""Pins the WIRING, not the arithmetic: reverting either call site to the
		break-free helper leaves working_hours at the raw span and turns this red.
		The maths itself is covered in TestTimeRules."""
		doc = _Doc(in_time=dt(9), out_time=dt(18))
		with (
			patch.object(att, "entered_break_minutes", return_value=60) as breaks,
			patch.object(att, "entered_shift_start", return_value=dt(9)) as start,
		):
			att.Attendance.apply_manual_times(doc)
		start.assert_called_once()
		self.assertEqual(start.call_args.args[0], "DAY", "trim against the row's own shift")
		self.assertEqual(doc.working_hours, 8.0, "the typed path must take the break off")
		breaks.assert_called_once()
		self.assertEqual(breaks.call_args.args[0], "DAY", "ask the row's own shift")

	def test_a_correction_after_submit_deducts_the_shifts_break(self):
		before = SimpleNamespace(in_time=dt(9), out_time=dt(17), working_hours=7.0)
		doc = _Doc(
			in_time=dt(9), out_time=dt(18), working_hours=7.0, auto_attendance=1, docstatus=1, _before=before
		)
		with (
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(att, "entered_break_minutes", return_value=105),  # a Friday
			patch.object(att, "entered_shift_start", return_value=None),
		):
			att.Attendance.before_update_after_submit(doc)
		self.assertEqual(doc.working_hours, 7.25, "a Friday correction takes 1h45m")

	def test_the_jobs_night_shift_row_is_not_refused(self):
		# The job anchors the day on the shift start; an early first punch at 23:50
		# the evening before is the employee being on time, not a bad entry.
		doc = _Doc(
			in_time=dt(23, 50, day=date(2026, 9, 7)), out_time=dt(8), working_hours=8.0, auto_attendance=1
		)
		att.Attendance.apply_manual_times(doc)  # must not throw
		self.assertEqual(doc.working_hours, 8.0)

	def test_a_resaved_automation_draft_is_not_refused_either(self):
		# The late-checkout repair resaves an existing auto draft with a later OUT;
		# for a night shift the IN still sits on the day before.
		before = SimpleNamespace(in_time=dt(23, 50, day=date(2026, 9, 7)), out_time=dt(6), working_hours=6.0)
		doc = _Doc(
			in_time=dt(23, 50, day=date(2026, 9, 7)),
			out_time=dt(8),
			working_hours=8.0,
			auto_attendance=1,
			_before=before,
		)
		att.Attendance.apply_manual_times(doc)  # must not throw
		self.assertEqual(doc.working_hours, 8.0, "the repair's own hours stand")

	def test_the_hourly_jobs_own_row_keeps_its_computed_hours(self):
		# breaks already deducted by the job; a raw span would overwrite 8.0 with 9.0
		doc = _Doc(in_time=dt(9), out_time=dt(18), working_hours=8.0, auto_attendance=1)
		att.Attendance.apply_manual_times(doc)
		self.assertEqual(doc.working_hours, 8.0)

	def test_correcting_a_submitted_row_recomputes_and_explains(self):
		before = SimpleNamespace(in_time=dt(9), out_time=dt(17), working_hours=8.0)
		doc = _Doc(
			in_time=dt(9), out_time=dt(18), working_hours=8.0, auto_attendance=1, docstatus=1, _before=before
		)
		with (
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(att, "entered_break_minutes", return_value=0),
			patch.object(att, "entered_shift_start", return_value=None),
		):
			att.Attendance.before_update_after_submit(doc)
		self.assertEqual(doc.working_hours, 9.0)
		self.assertTrue(getattr(doc, "overtime_recomputed", False))
		self.assertTrue(any("17:00" in c and "18:00" in c for c in doc.comments), doc.comments)

	def test_an_unrelated_submitted_edit_changes_nothing(self):
		before = SimpleNamespace(in_time=dt(9), out_time=dt(18), working_hours=8.0)
		doc = _Doc(
			in_time=dt(9), out_time=dt(18), working_hours=8.0, auto_attendance=1, docstatus=1, _before=before
		)
		att.Attendance.before_update_after_submit(doc)
		self.assertEqual(doc.working_hours, 8.0)
		self.assertEqual(doc.comments, [])


if __name__ == "__main__":
	unittest.main()


class TestATypedCorrectionUsesTheSameThreeRules(unittest.TestCase):
	"""A corrected day and an automatic day must agree about the same times.

	The hourly job applies THREE rules to turn times into paid hours: the unpaid
	break, the unpaid early arrival (`paid_intervals_from`, HR's ruling of
	10 Sep 2026 — "early clock in didnt counted as paid"), and hours counted
	from worked intervals rather than the raw span. cf4cb2fe4 unified the break
	only, and review found the gap this closes.

	The case it costs money on: shift 09:00-18:00, employee punches in 07:30 and
	out at 18:00. The job writes 8.00. HR then corrects the out time by five
	minutes, the row recomputes from 07:30, and it becomes 9.58 against the
	job's own 8.08 for those times — +1.50 h, from a five-minute edit. It never
	self-heals either: correcting a row sets auto_attendance to 0, so the job
	never revisits it.

	Nabil, 11 Sep 2026, on re-applying the rule: "i agree.. it need to be
	corrected, i saw it."

	Order matters as much as the rules. The break is measured on the TRIMMED
	interval, not the raw span — `paid_intervals_from` says so in its own
	docstring: a break configured before the shift starts must not be taken off
	hours that were never counted.
	"""

	def test_an_early_arrival_is_not_paid_on_a_typed_correction(self):
		# 07:30 in, 18:05 out, 9-6 shift, one hour of break: 09:00-18:05 less 60m.
		self.assertEqual(
			att.entered_paid_hours(dt(7, 30), dt(18, 5), shift_start=dt(9), break_minutes=60), 8.08
		)

	def test_the_reviewers_case_lands_on_the_jobs_own_answer(self):
		self.assertEqual(att.entered_paid_hours(dt(7, 30), dt(18), shift_start=dt(9), break_minutes=60), 8.0)

	def test_a_late_arrival_is_not_credited_anything(self):
		# Trimming only ever removes; it never extends a day backwards.
		self.assertEqual(att.entered_paid_hours(dt(9, 30), dt(18), shift_start=dt(9), break_minutes=60), 7.5)

	def test_without_a_shift_start_the_span_stands(self):
		# A row with no shift resolved has nothing to trim against.
		self.assertEqual(att.entered_paid_hours(dt(7, 30), dt(18), shift_start=None, break_minutes=60), 9.5)

	def test_work_entirely_before_the_shift_is_not_paid(self):
		# An interval that ENDS before the shift starts is dropped whole — there is
		# no part of it inside the paid day. (An interval that STRADDLES the start
		# keeps its later half; that is the case above.)
		self.assertEqual(att.entered_paid_hours(dt(7), dt(8), shift_start=dt(9), break_minutes=0), 0.0)

	def test_a_night_shift_starting_late_in_the_day_trims_correctly(self):
		# 22:00 shift, punched in 21:50, out 06:00 next morning, no break.
		self.assertEqual(
			att.entered_paid_hours(
				dt(21, 50), dt(6, day=date(2026, 9, 9)), shift_start=dt(22), break_minutes=0
			),
			8.0,
		)
