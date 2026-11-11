"""A half day is not closed while the person may still punch (owner, 11 Nov 2026).

Live: Irfan's half-day leave row (afternoon off, approved the day before) was
closed by the hourly job during his own morning shift: `mark_absent_for_half_day_dates`
took every waiting Half Day dated on or before the last check-in sync, which on the
day itself is mid-shift. His 09:01 IN and 13:33 OUT then arrived to a row no
longer waiting, were linked as evidence, and the hours stayed 0.00.

The wait now ends on the same rule the absent sweep uses: only for days up to the
shift BEFORE the last sync, i.e. once the day's shift (with its check-out allowance)
is over.

    python3 -m pytest -q hrms/tests/test_half_day_waits_for_the_shift.py
"""

import ast
import pathlib
import unittest
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hr/doctype/shift_type/shift_type.py"


def _method(name):
	tree = ast.parse(SOURCE.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ShiftType")
	return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


class TestTheHalfDayWaitUsesTheShiftEnd(unittest.TestCase):
	def test_it_reads_the_same_end_date_as_the_absent_sweep(self):
		body = ast.unparse(_method("mark_absent_for_half_day_dates"))
		self.assertIn("get_start_and_end_dates(employee)", body)
		# the sync's own date is never the cutoff (it is mid-shift on the day itself)
		self.assertNotIn("'<=', getdate(self.last_sync_of_checkin)", body)

	def test_no_end_date_means_nothing_is_closed(self):
		body = ast.unparse(_method("mark_absent_for_half_day_dates"))
		self.assertIn("if not end_date", body)


class TestWhichDaysMayClose(unittest.TestCase):
	"""half_days_to_close(rows, end_date) is pure: the rows dated on or before end_date."""

	def test_today_waits_while_yesterday_closes(self):
		from hrms.utils.half_day_session import half_days_to_close

		rows = [
			{"name": "ATT-YESTERDAY", "attendance_date": date(2026, 11, 9)},
			{"name": "ATT-TODAY", "attendance_date": date(2026, 11, 10)},
		]
		# end_date = the last shift fully over before the sync (the 9th, during the 10th's shift)
		self.assertEqual([r["name"] for r in half_days_to_close(rows, date(2026, 11, 9))], ["ATT-YESTERDAY"])

	def test_no_end_date_closes_nothing(self):
		from hrms.utils.half_day_session import half_days_to_close

		self.assertEqual(half_days_to_close([{"name": "A", "attendance_date": date(2026, 11, 1)}], None), [])


if __name__ == "__main__":
	unittest.main()


class TestReviewOfTheHalfDayFix(unittest.TestCase):
	"""Review of 47b3fc2f2 / c552c5e90 / 7fec2d6f2 (11 Nov 2026)."""

	def test_a_mixed_shift_employee_still_has_a_cutoff(self):
		# get_start_and_end_dates answers (None, None) when the shift before the
		# last sync is another Shift Type; the half day must not wait for ever
		body = ast.unparse(_method("mark_absent_for_half_day_dates"))
		self.assertIn("half_day_cutoff(", body)

	def test_the_cutoff_falls_back_to_the_day_before_the_last_sync(self):
		from hrms.utils.half_day_session import half_day_cutoff

		self.assertEqual(half_day_cutoff(date(2026, 11, 9), date(2026, 11, 11)), date(2026, 11, 9))
		self.assertEqual(
			half_day_cutoff(None, date(2026, 11, 11)), date(2026, 11, 9)
		)  # two days back: a night shift dated the 10th ends on the 11th
		self.assertIsNone(half_day_cutoff(None, None))

	def test_a_closed_half_day_is_never_refilled_over_a_paid_day(self):
		source = (ROOT / "hr/doctype/employee_checkin/employee_checkin.py").read_text()
		start = source.index("def get_existing_half_day_attendance")
		body = source[start : source.index("\ndef ", start + 10)]
		self.assertIn("_repair_financial_dependency", body)

	def test_the_repair_skips_paid_days_and_mirrored_rows(self):
		source = (ROOT / "patches/v16_0/fill_half_day_leave_hours.py").read_text()
		self.assertIn("_repair_financial_dependency", source)
		self.assertIn('"synced_from_instance": ("is", "not set")', source)
