"""A half day off is not a late arrival (owner, 25 Sep 2026).

AM off -> the day starts at the middle of the shift, so arriving then is on
time. PM off -> the day ends at the middle of the shift, so leaving then is
not early. Grace still applies. A half day with no session (every request
made before this release) keeps today's rule: no guessing.

PYTHONPATH=. python3 -m pytest -q hrms/utils/test_half_day_session.py
"""

import unittest
from datetime import datetime

from hrms.utils.half_day_session import late_early_bounds, session_hint

S, E = datetime(2026, 10, 14, 9, 0), datetime(2026, 10, 14, 18, 0)


class TestBounds(unittest.TestCase):
	def test_no_session_is_the_whole_shift(self):
		self.assertEqual(late_early_bounds(S, E, None), (S, E))
		self.assertEqual(late_early_bounds(S, E, ""), (S, E))

	def test_am_off_starts_the_day_at_midshift(self):
		self.assertEqual(late_early_bounds(S, E, "AM"), (datetime(2026, 10, 14, 13, 30), E))

	def test_pm_off_ends_the_day_at_midshift(self):
		self.assertEqual(late_early_bounds(S, E, "PM"), (S, datetime(2026, 10, 14, 13, 30)))

	def test_night_shift_midpoint_crosses_midnight(self):
		start, end = datetime(2026, 10, 14, 21, 0), datetime(2026, 10, 15, 6, 0)
		self.assertEqual(late_early_bounds(start, end, "AM")[0], datetime(2026, 10, 15, 1, 30))

	def test_unknown_session_is_ignored_not_guessed(self):
		self.assertEqual(late_early_bounds(S, E, "Evening"), (S, E))


class TestHint(unittest.TestCase):
	def test_the_words_the_employee_reads(self):
		self.assertEqual(session_hint(S, E, "AM"), ("13:30", "Off in the morning. Start by 13:30."))
		self.assertEqual(session_hint(S, E, "PM"), ("13:30", "Off in the afternoon. Leave at 13:30."))
		self.assertEqual(session_hint(S, E, None), (None, ""))


class TestLeaveRules(unittest.TestCase):
	def test_a_new_half_day_must_say_which_half(self):
		from hrms.utils.half_day_session import session_problem

		self.assertEqual(session_problem(half_day=1, session="", is_new=True), "missing")
		self.assertIsNone(session_problem(half_day=1, session="AM", is_new=True))
		self.assertIsNone(session_problem(half_day=0, session="", is_new=True))

	def test_a_request_saved_before_this_release_is_left_alone(self):
		from hrms.utils.half_day_session import session_problem

		self.assertIsNone(session_problem(half_day=1, session="", is_new=False))

	def test_same_half_twice_on_one_date_clashes_but_am_plus_pm_does_not(self):
		from hrms.utils.half_day_session import sessions_clash

		self.assertTrue(sessions_clash("AM", "AM"))
		self.assertFalse(sessions_clash("AM", "PM"))
		# an old request with no session cannot be told apart: keep the old rule
		self.assertIsNone(sessions_clash("AM", ""))


class TestRowFlags(unittest.TestCase):
	"""An already-marked day gets its late/early flags from the half's line."""

	def flags(self, in_t, out_t, session, grace=(15, 15)):
		from hrms.utils.half_day_session import flags_for

		return flags_for(
			in_time=in_t,
			out_time=out_t,
			shift_start=S,
			shift_end=E,
			session=session,
			late_grace=grace[0],
			early_grace=grace[1],
			late_on=True,
			early_on=True,
		)

	def test_am_off_in_at_midshift_plus_grace_is_on_time(self):
		self.assertEqual(
			self.flags(datetime(2026, 10, 14, 13, 45), E, "AM"), {"late_entry": 0, "early_exit": 0}
		)

	def test_am_off_in_past_grace_is_late(self):
		self.assertEqual(self.flags(datetime(2026, 10, 14, 13, 46), E, "AM")["late_entry"], 1)

	def test_pm_off_out_at_midshift_is_not_early(self):
		self.assertEqual(
			self.flags(S, datetime(2026, 10, 14, 13, 30), "PM"), {"late_entry": 0, "early_exit": 0}
		)

	def test_marking_switched_off_on_the_shift_marks_nothing(self):
		from hrms.utils.half_day_session import flags_for

		out = flags_for(
			in_time=datetime(2026, 10, 14, 15, 0),
			out_time=E,
			shift_start=S,
			shift_end=E,
			session="AM",
			late_grace=0,
			early_grace=0,
			late_on=False,
			early_on=False,
		)
		self.assertEqual(out, {"late_entry": 0, "early_exit": 0})

	def test_no_times_no_flags(self):
		self.assertEqual(self.flags(None, None, "AM"), {"late_entry": 0, "early_exit": 0})


class TestHintsForTheForm(unittest.TestCase):
	def test_both_halves_from_one_shift(self):
		from hrms.utils.half_day_session import hints_for

		self.assertEqual(
			hints_for(S, E),
			{
				"midpoint": "13:30",
				"shift": "09:00–18:00",
				"AM": "Off in the morning. Start by 13:30.",
				"PM": "Off in the afternoon. Leave at 13:30.",
				"AM_short": "start 13:30",
				"PM_short": "leave 13:30",
			},
		)

	def test_no_shift_that_day_says_so_plainly(self):
		from hrms.utils.half_day_session import hints_for

		self.assertEqual(
			hints_for(None, None),
			{
				"midpoint": None,
				"shift": None,
				"AM": "Off in the morning.",
				"PM": "Off in the afternoon.",
				"AM_short": "",
				"PM_short": "",
			},
		)
