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

import pathlib
import re
import unittest
from typing import ClassVar

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.hr.doctype.shift_type import shift_type as st

DAY = "2026-09-04"


def tap(time, log_type, **extra):
	return {"time": f"{DAY} {time}", "log_type": log_type, **extra}


IGNORED = {"skip_auto_attendance": 1, "skipped_as_noise": 1}
#: skipped, but nobody judged it — the system merely deferred the batch
DEFERRED = {"skip_auto_attendance": 1}
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

	def test_a_tap_the_system_merely_deferred_is_still_a_wall(self):
		"""`handle_attendance_exception` skip-stamps punches when a rebuild is
		refused by the financial guard. Nobody judged those; the system gave up
		on the batch. Found in review of ff1493e85, which read them as noise."""
		self.assertTrue(st.splits_the_day(tap("12:00", "OUT", **DEFERRED)))

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

	def test_a_deferred_tap_still_separates_the_spans(self):
		logs = [tap("09:00", "IN"), tap("12:00", "OUT", **DEFERRED), tap("18:00", "OUT")]
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


class EveryModuleThatSkipsAPunchIsClassifiedCase(unittest.TestCase):
	"""The safety of this change rests on ONE claim: nothing sets
	`skip_auto_attendance` to mean "unverified evidence sitting inside an
	otherwise good day" except the reject path, which `splits_the_day` catches.

	A claim in a commit message rots, and my own first list of writers was
	incomplete — it missed the master editor's two. So this reads the app. It
	asserts the set of MODULES, not a line count: a refactor inside one of them
	is not news, a new module touching the tick is.

	Since the review of ff1493e85 the DEFAULT is the wall, so this list is no
	longer load-bearing for safety — a writer that says nothing gets the old,
	conservative reading. It is still the map of who means what.

	NOISE — ticks `skipped_as_noise`, so the day reads straight across it:
	  * api/attendance_fix_day.py — HR ignored it, or the rebuild did.
	  * api/remote_checkin.py — a burst stutter, "stored, not counted".

	WALL — skipped without that tick, so the spans stay apart:
	  * overrides/remote_checkin_request_hooks.py — the approver rejected it.
	  * hr/doctype/employee_checkin/employee_checkin.py — `attendance_status ==
	    "Skip"`, and `handle_attendance_exception` when the financial guard
	    refuses a rebuild. The system DEFERRED those; nobody judged them. This
	    is the case the first version of this rule got wrong.
	  * api/attendance_master_edit.py — a device punch HR superseded with their
	    own typed time. Arguably noise, deliberately left a wall: HR restated
	    the day themselves, so there is no span to bridge anyway.

	NEVER REACHES THIS CALCULATION — the whole day is refused upstream:
	  * utils/hr_removed_day.py and api/attendance_master_edit.py — a day HR
	    removed in Shift Attendance.
	"""

	WRITERS: ClassVar[frozenset] = frozenset(
		{
			"hrms/api/attendance_fix_day.py",
			"hrms/api/attendance_master_edit.py",
			"hrms/api/remote_checkin.py",
			"hrms/hr/doctype/employee_checkin/employee_checkin.py",
			"hrms/overrides/remote_checkin_request_hooks.py",
			"hrms/utils/hr_removed_day.py",
		}
	)

	def test_no_unclassified_module_skips_a_punch(self):
		root = pathlib.Path(__file__).resolve().parents[2]
		found = set()
		for path in sorted((root / "hrms").rglob("*.py")):
			rel = path.relative_to(root).as_posix()
			if "test" in pathlib.Path(rel).name or "/tests/" in rel:
				continue
			for line in path.read_text().splitlines():
				if "skip_auto_attendance" not in line or line.lstrip().startswith("#"):
					continue
				if re.search(r'skip_auto_attendance"?\s*(=|:|,)\s*(1|value)\b', line) or re.search(
					r'\.set\("skip_auto_attendance", 1\)|_set_skip\(', line
				):
					found.add(rel)
		unclassified = found - self.WRITERS
		self.assertEqual(
			unclassified,
			set(),
			"a new module skips punches — say in this test's docstring whether that means "
			"NOISE (dropped from the day) or a WALL (splits_the_day), then list it here",
		)

	def test_the_classified_writers_are_all_still_there(self):
		"""The other direction: a module that stops skipping punches should not
		leave a stale name in the list pretending to be covered."""
		root = pathlib.Path(__file__).resolve().parents[2]
		for rel in sorted(self.WRITERS):
			with self.subTest(module=rel):
				self.assertIn("skip_auto_attendance", (root / rel).read_text())


class TheVerdictGoesWithTheSkipCase(unittest.TestCase):
	"""Clearing the skip clears the noise verdict, everywhere.

	A tap that counts again is not a judgement about anything. A tick left
	behind on it would make the NEXT skip — possibly one the system merely
	deferred — read as noise, which is the very thing the default protects
	against.
	"""

	#: (file, the anchor the clearing code follows). Anchored on the DEFINITION,
	#: not the name: every one of these is also called earlier in its own file.
	CLEARERS: ClassVar[tuple] = (
		("hrms/api/attendance_fix_day.py", "def restore_tap("),
		("hrms/api/attendance_master_edit.py", "def _set_skip("),
		("hrms/utils/attendance_recovery.py", 'elif action == "unskip":'),
	)

	def test_every_place_that_unskips_also_clears_the_verdict(self):
		root = pathlib.Path(__file__).resolve().parents[2]
		for rel, marker in self.CLEARERS:
			with self.subTest(where=f"{rel}:{marker}"):
				text = (root / rel).read_text()
				start = text.index(marker)
				window = text[start : start + 1200]
				self.assertIn(
					"skipped_as_noise",
					window,
					f"{rel} clears the skip near {marker} without clearing the verdict",
				)


class TheColumnMayNotExistYetCase(unittest.TestCase):
	"""A SELECT naming a column a site has not caught up with dies with
	"Unknown column" — this fork has been bitten by exactly that before
	(`ensure_extension_custom_fields`, and the OT suite falling over on
	`remote_approval_status`). So the noise verdict is asked for only when the
	column is there, and its absence reads as the WALL.
	"""

	def test_the_field_is_not_in_the_static_list(self):
		self.assertNotIn(st.NOISE_FIELD, st.CHECKIN_FIELDS)

	def test_a_row_without_the_column_is_a_wall(self):
		row = tap("11:44", "OUT", skip_auto_attendance=1)  # no skipped_as_noise key at all
		self.assertTrue(st.splits_the_day(row))

	def test_the_reader_asks_for_it_only_when_the_column_exists(self):
		source = pathlib.Path(st.__file__).read_text()
		self.assertNotIn("fields=list(CHECKIN_FIELDS)", source, "read through checkin_fields()")
		self.assertIn("has_column", source)


if __name__ == "__main__":
	unittest.main()
