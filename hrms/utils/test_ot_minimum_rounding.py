"""The 30-minute rounding is applied BEFORE the minimum, not after.

HR, 10 Sep 2026: "at 50 minutes and above auto rounded to 60m so i am eligible
for OT Pay."

The old order threw the day away first: a raw 56m59s was compared against the
60-minute minimum, failed, and `continue`d — so the rounding that would have
carried it to a full hour never ran. Every day landing in the 50-59 minute band
paid nothing at all. Real case: HR-ATT-2026-16073, 9 Sep 2026, in 10:12:02, out
20:09:01 on a 9-6 shift — 56m59s past the late-adjusted window, paid 0.

Only that band moves. 49 minutes still rounds to the half hour and still fails a
60-minute minimum; 70 minutes passed before and passes now.

Pure — no site, so the commit gate runs it on the system interpreter.
"""

import unittest

from hrms.utils.ot_calculation import ot_minutes_qualify

MIN = 60


def m(minutes):
	"""Minutes as the fractional hours the engine carries."""
	return minutes / 60.0


class TestOtMinimumRounding(unittest.TestCase):
	def test_the_50_to_59_band_rounds_up_and_qualifies(self):
		# HR's sentence, as assertions.
		self.assertTrue(ot_minutes_qualify(m(50), MIN), "50m rounds to the hour")
		self.assertTrue(ot_minutes_qualify(m(56) + 59 / 3600, MIN), "9 Sep: 56m59s")
		self.assertTrue(ot_minutes_qualify(m(59), MIN))

	def test_below_50_minutes_still_fails_a_60_minute_minimum(self):
		# 30-49 rounds to the HALF hour, which is still short of 60.
		self.assertFalse(ot_minutes_qualify(m(49), MIN))
		self.assertFalse(ot_minutes_qualify(m(30), MIN))
		# under 30 rounds to nothing at all
		self.assertFalse(ot_minutes_qualify(m(29), MIN))
		self.assertFalse(ot_minutes_qualify(m(1), MIN))

	def test_days_that_already_qualified_are_untouched(self):
		self.assertTrue(ot_minutes_qualify(m(60), MIN))
		self.assertTrue(ot_minutes_qualify(m(70), MIN))  # 7 Sep
		self.assertTrue(ot_minutes_qualify(m(73), MIN))  # 4 Sep
		self.assertTrue(ot_minutes_qualify(3.0, MIN))

	def test_a_shorter_configured_minimum_rounds_the_same_way(self):
		# A shift set to 30 minutes: the half-hour band now reaches it.
		self.assertTrue(ot_minutes_qualify(m(30), 30))
		self.assertTrue(ot_minutes_qualify(m(49), 30))
		self.assertFalse(ot_minutes_qualify(m(29), 30))

	def test_no_minimum_configured_admits_everything(self):
		# Unchanged from the old `hours * 60 < 0` comparison, which never skipped.
		self.assertTrue(ot_minutes_qualify(m(1), 0))
		self.assertTrue(ot_minutes_qualify(m(29), 0))

	def test_nothing_worked_never_qualifies(self):
		self.assertFalse(ot_minutes_qualify(0, MIN))
		self.assertFalse(ot_minutes_qualify(-1, MIN))
