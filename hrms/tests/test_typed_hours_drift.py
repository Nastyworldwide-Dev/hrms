"""A day HR corrected before the early-arrival fix still holds the inflated hours.

Review of 19c939278: that commit made typed corrections apply the early-arrival
trim GOING FORWARD only, and its own docstring says why nothing self-heals —
correcting a row sets `auto_attendance` to 0, so the hourly job never revisits
it. The same session shipped a repair for `ot_hours` and none for
`working_hours`.

So a day corrected before the fix, on a shift starting 09:00 with a 07:30 punch,
still reads 9.58 where the job's own answer is 8.08 — and payroll pays the 9.58.
That is the exact case the commit message cites as costing money, left in the
data.

Nabil authorised "repair last 2 months", which covers this as much as it covers
the overtime.

Pure: which rows have drifted, and by how much, is the decision worth pinning.
"""

import unittest

from hrms.hr.doctype.attendance.attendance import typed_hours_drift

ROW = {"attendance": "ATT-1", "employee": "EMP-1", "date": "2026-09-09"}


class TestTypedHoursDrift(unittest.TestCase):
	def test_a_row_whose_stored_hours_differ_is_reported(self):
		drift = typed_hours_drift([dict(ROW, stored=9.58, correct=8.08)])
		self.assertEqual(len(drift), 1)
		self.assertEqual(drift[0]["old_working_hours"], 9.58)
		self.assertEqual(drift[0]["new_working_hours"], 8.08)

	def test_a_row_already_correct_is_not_touched(self):
		self.assertEqual(typed_hours_drift([dict(ROW, stored=8.08, correct=8.08)]), [])

	def test_a_rounding_tail_is_not_drift(self):
		# Stored values carry two decimals; a difference below that is noise, and
		# rewriting a submitted row over noise is all risk and no benefit.
		self.assertEqual(typed_hours_drift([dict(ROW, stored=8.08, correct=8.084)]), [])
		self.assertEqual(
			typed_hours_drift([dict(ROW, stored=8.08, correct=8.09)])[0]["new_working_hours"], 8.09
		)

	def test_drift_in_either_direction_is_reported(self):
		# The trim usually lowers hours, but a corrected break can raise them.
		self.assertEqual(len(typed_hours_drift([dict(ROW, stored=7.0, correct=8.08)])), 1)

	def test_the_row_keeps_its_identity_for_the_guard_and_the_report(self):
		drift = typed_hours_drift([dict(ROW, stored=9.58, correct=8.08)])
		self.assertEqual(drift[0]["employee"], "EMP-1")
		self.assertEqual(drift[0]["date"], "2026-09-09")
		self.assertEqual(drift[0]["attendance"], "ATT-1")


class TestARepairNeverZeroesAPaidDay(unittest.TestCase):
	"""Computing 0 where a positive figure is stored is a deletion, not a repair.

	Found by forcing the write path on the verify bench, 11 Sep 2026. The row
	picked was a NIGHT shift starting 19:00; the probe's in/out times both fell
	before that, so `paid_intervals_from` dropped the whole interval and the
	repair wrote 0.0 over a stored 10.5.

	The arithmetic was right for those times. The behaviour is not: any row whose
	whole span precedes its shift start — a mis-stamped shift, a row built by a
	path that dated it differently, a night shift whose date convention drifted —
	would have its day silently erased by a migrate.

	A repair may lower hours. It may not delete a day. Those rows are REPORTED,
	with the same wording as a financially-locked day, and left alone.
	"""

	def test_zero_over_a_positive_stored_value_is_refused(self):
		drift = typed_hours_drift([dict(ROW, stored=10.5, correct=0.0)])
		self.assertEqual(drift, [], "a day that computes to nothing is not repaired")

	def test_zero_over_zero_is_simply_not_drift(self):
		self.assertEqual(typed_hours_drift([dict(ROW, stored=0.0, correct=0.0)]), [])

	def test_a_genuine_reduction_is_still_repaired(self):
		# The whole point of the fix: 9.58 -> 8.08 must still land.
		drift = typed_hours_drift([dict(ROW, stored=9.58, correct=8.08)])
		self.assertEqual(drift[0]["new_working_hours"], 8.08)

	def test_a_row_that_was_always_zero_can_still_gain_hours(self):
		# Raising from 0 is not the dangerous direction.
		drift = typed_hours_drift([dict(ROW, stored=0.0, correct=8.0)])
		self.assertEqual(drift[0]["new_working_hours"], 8.0)
