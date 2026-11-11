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
		self.assertNotIn("getdate(self.last_sync_of_checkin)", body)

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
