"""The OT backfill must refuse a day a payout already depends on.

Nabil, 11 Sep 2026: "repair last 2 months."

The rounding fix (2fc1db148) changed what `Attendance.ot_hours` SHOULD hold for
every weekday in the 50-59 minute band, but only going forward. Old rows still
read 0 while the claim card recomputes from punches and offers the same day —
record and card disagree on the employee's screen, and a day showing 0 is a day
nobody opens.

`recompute_ot_backfill` is the only tool that can repair them, and as written it
rewrites EVERY submitted row in a range with no financial-dependency check at
all, then commits. The attendance repair tool beside it refuses such days
(`attendance_day_audit._financially_locked` ->
`remote_checkin_hooks._repair_financial_dependency`, which looks for approved
overtime, replacement leave and submitted payroll). The backfill had no
equivalent, which is why it was bench-only and why running it on deploy would
have rewritten already-paid days.

Pure — the partition is the decision worth pinning; no site needed.
"""

import unittest

from hrms.hr.doctype.attendance.attendance import backfill_rows_to_write

ROWS = [
	{"attendance": "ATT-1", "employee": "EMP-1", "date": "2026-09-09"},
	{"attendance": "ATT-2", "employee": "EMP-2", "date": "2026-09-09"},
	{"attendance": "ATT-3", "employee": "EMP-1", "date": "2026-08-20"},
]


class TestBackfillRowsToWrite(unittest.TestCase):
	def test_a_locked_day_is_never_written(self):
		write, skipped = backfill_rows_to_write(ROWS, locked={("EMP-1", "2026-09-09")})
		self.assertEqual([r["attendance"] for r in write], ["ATT-2", "ATT-3"])
		self.assertEqual([r["attendance"] for r in skipped], ["ATT-1"])

	def test_nothing_locked_writes_everything(self):
		write, skipped = backfill_rows_to_write(ROWS, locked=set())
		self.assertEqual(len(write), 3)
		self.assertEqual(skipped, [])

	def test_everything_locked_writes_nothing(self):
		locked = {(r["employee"], r["date"]) for r in ROWS}
		write, skipped = backfill_rows_to_write(ROWS, locked=locked)
		self.assertEqual(write, [])
		self.assertEqual(len(skipped), 3)

	def test_the_lock_is_per_employee_AND_date_not_either(self):
		# EMP-1 is locked on the 9th only; their August day must still repair,
		# and EMP-2's 9th must not be caught by EMP-1's lock.
		write, _ = backfill_rows_to_write(ROWS, locked={("EMP-1", "2026-09-09")})
		self.assertIn("ATT-3", [r["attendance"] for r in write])
		self.assertIn("ATT-2", [r["attendance"] for r in write])

	def test_a_skipped_row_keeps_its_figures_for_the_report(self):
		# HR has to be able to see what was left alone and what it would have become.
		rows = [dict(ROWS[0], old_ot_hours=0.0, new_ot_hours=1.0)]
		_write, skipped = backfill_rows_to_write(rows, locked={("EMP-1", "2026-09-09")})
		self.assertEqual(skipped[0]["old_ot_hours"], 0.0)
		self.assertEqual(skipped[0]["new_ot_hours"], 1.0)
