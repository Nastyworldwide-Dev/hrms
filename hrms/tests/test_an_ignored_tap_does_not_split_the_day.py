"""A tap HR ignored is removed from the day, not made a wall across it.

Live, 17 Sep 2026, Norazlin's 4 September, after HR corrected every tap on it
with Fix Day. The punches read, in order:

    09:03:34 IN   counted
    11:44:06 OUT  skipped   (the accidental mid-day out)
    18:09:14 IN   skipped   (the 16-second glitch burst)
    18:09:26 OUT  counted
    18:09:30 IN   skipped   (the same burst)

and the day came back "Half Day · in 09:03 · out — · 0 h worked".

`ShiftType.get_attendance` groups logs into CONTIGUOUS eligible segments:

    segments = [g for eligible, g in groupby(logs, counts_for_attendance) if eligible]

The three skipped taps sit BETWEEN the real IN and the real OUT, so the two
counted taps landed in two segments of one tap each and never paired. Under
alternating pairing a one-tap segment has no out time at all, which is why the
day showed an in and no out.

The wall is deliberate and stays — for a punch that is not verified evidence. An
OFF-SHIFT punch, a REJECTED one and a late check-out still waiting for its
approver each separate two spans, and bridging them would pay unverified time.
A tap somebody deliberately ignored is different: "ignore" means the tap is not
there, and the taps around it are one session. Owner ruling, 17 Sep 2026: "the
11 am out is possible accidental and should be fine for us to fix by removing it
alongside the broken glitch stuff. applicable to any scenarios."

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_an_ignored_tap_does_not_split_the_day.py
"""

from __future__ import annotations

import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.hr.doctype.shift_type import shift_type as st

DAY = "2026-09-04"


def tap(time, log_type, **extra):
	return {"time": f"{DAY} {time}", "log_type": log_type, **extra}


IGNORED = {"skip_auto_attendance": 1}
REJECTED = {"skip_auto_attendance": 1, "remote_approval_status": "Rejected"}
OFF_SHIFT = {"offshift": 1}
PENDING_LATE = {"remote_approval_status": "Pending", "is_late_checkout": 1}

#: Norazlin's day, exactly as Fix Day left it.
NORAZLIN = [
	tap("09:03:34", "IN"),
	tap("11:44:06", "OUT", **IGNORED),
	tap("18:09:14", "IN", **IGNORED),
	tap("18:09:26", "OUT"),
	tap("18:09:30", "IN", **IGNORED),
]


class WhatStillSeparatesTwoSpansCase(unittest.TestCase):
	"""`splits_the_day` is the wall; `counts_for_attendance` is the evidence."""

	def test_an_off_shift_punch_is_a_wall(self):
		self.assertTrue(st.splits_the_day(tap("12:00", "OUT", **OFF_SHIFT)))

	def test_a_rejected_punch_is_a_wall(self):
		self.assertTrue(st.splits_the_day(tap("12:00", "OUT", **REJECTED)))

	def test_a_late_check_out_awaiting_its_approver_is_a_wall(self):
		self.assertTrue(st.splits_the_day(tap("20:00", "OUT", **PENDING_LATE)))

	def test_a_tap_somebody_ignored_is_not_a_wall(self):
		self.assertFalse(st.splits_the_day(tap("11:44", "OUT", **IGNORED)))

	def test_a_counted_tap_is_not_a_wall(self):
		self.assertFalse(st.splits_the_day(tap("09:03", "IN")))

	def test_nothing_is_both_evidence_and_a_wall(self):
		for row in [
			*NORAZLIN,
			tap("12:00", "OUT", **REJECTED),
			tap("12:00", "OUT", **OFF_SHIFT),
			tap("20:00", "OUT", **PENDING_LATE),
		]:
			with self.subTest(row=row["time"]):
				self.assertFalse(st.counts_for_attendance(row) and st.splits_the_day(row))


class TheDayIsSegmentedAroundWallsOnlyCase(unittest.TestCase):
	def segments(self, logs):
		return [[row["time"][11:] for row in segment] for segment in st.attendance_segments(logs)]

	def test_norazlins_day_is_one_session(self):
		self.assertEqual(self.segments(NORAZLIN), [["09:03:34", "18:09:26"]])

	def test_a_rejected_punch_still_separates_the_spans(self):
		logs = [
			tap("09:00", "IN"),
			tap("12:00", "OUT", **REJECTED),
			tap("13:00", "IN"),
			tap("18:00", "OUT"),
		]
		self.assertEqual(self.segments(logs), [["09:00"], ["13:00", "18:00"]])

	def test_an_off_shift_punch_still_separates_the_spans(self):
		logs = [tap("09:00", "IN"), tap("12:00", "OUT", **OFF_SHIFT), tap("18:00", "OUT")]
		self.assertEqual(self.segments(logs), [["09:00"], ["18:00"]])

	def test_a_clean_day_is_untouched(self):
		logs = [tap("09:00", "IN"), tap("18:00", "OUT")]
		self.assertEqual(self.segments(logs), [["09:00", "18:00"]])

	def test_a_day_of_nothing_but_ignored_taps_has_no_segment(self):
		self.assertEqual(self.segments([tap("09:00", "IN", **IGNORED)]), [])

	def test_ignored_taps_around_a_wall_do_not_resurrect_the_span(self):
		logs = [
			tap("09:00", "IN"),
			tap("10:00", "OUT", **IGNORED),
			tap("12:00", "OUT", **REJECTED),
			tap("13:00", "IN", **IGNORED),
			tap("18:00", "OUT"),
		]
		self.assertEqual(self.segments(logs), [["09:00"], ["18:00"]])


if __name__ == "__main__":
	unittest.main()
