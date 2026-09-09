"""A punch belongs to the shift it was worked in, not the shift whose start is nearest.

PYTHONPATH=. python3 hrms/tests/test_shift_resolution.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.utils.shift_resolution import choose_shift, superseded_assignments

HRMS = pathlib.Path(__file__).resolve().parent.parent
D = date(2026, 9, 7)


def _cand(shift, start, end, grace=60):
	return {
		"shift_type": shift,
		"start_datetime": start,
		"end_datetime": end,
		"actual_start": start - timedelta(minutes=grace),
		"actual_end": end + timedelta(minutes=grace),
	}


def _day():
	return _cand("10AM-7PM", datetime(2026, 9, 7, 10), datetime(2026, 9, 7, 19))


def _night(day=7):
	return _cand("7PM-3:30AM", datetime(2026, 9, day, 19), datetime(2026, 9, day + 1, 3, 30))


class TestChooseShift(unittest.TestCase):
	def test_the_out_closes_the_shift_of_its_in_even_when_another_start_is_nearer(self):
		"""HR's case: IN 09:35 on the day shift, OUT 19:45. 19:00 is 45 minutes
		away, 10:00 nine hours; the old rule sent the OUT to the night shift."""
		open_in = {"shift": "10AM-7PM", "time": datetime(2026, 9, 7, 9, 35)}
		chosen = choose_shift(datetime(2026, 9, 7, 19, 45), "OUT", [_day(), _night()], open_in)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")

	def test_an_in_goes_to_the_window_it_falls_in(self):
		chosen = choose_shift(datetime(2026, 9, 7, 9, 35), "IN", [_day(), _night()], None)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")

	def test_a_night_out_after_midnight_belongs_to_yesterdays_shift(self):
		open_in = {"shift": "7PM-3:30AM", "time": datetime(2026, 9, 7, 19, 5)}
		chosen = choose_shift(datetime(2026, 9, 8, 3, 40), "OUT", [_day(), _night(7), _night(8)], open_in)
		self.assertEqual(chosen["shift_type"], "7PM-3:30AM")
		self.assertEqual(chosen["start_datetime"], datetime(2026, 9, 7, 19))

	def test_a_punch_in_no_window_is_off_shift_not_guessed(self):
		self.assertIsNone(choose_shift(datetime(2026, 9, 7, 6, 0), "IN", [_day(), _night()], None))

	def test_two_containing_windows_take_the_nearest_start(self):
		nine = _cand("9AM-6PM", datetime(2026, 9, 7, 9), datetime(2026, 9, 7, 18))
		self.assertEqual(
			choose_shift(datetime(2026, 9, 7, 8, 50), "IN", [nine, _day()], None)["shift_type"], "9AM-6PM"
		)
		self.assertEqual(
			choose_shift(datetime(2026, 9, 7, 9, 40), "IN", [nine, _day()], None)["shift_type"], "10AM-7PM"
		)

	def test_an_in_from_a_previous_session_does_not_bind_a_new_out(self):
		"""An IN 30 hours ago is not the session this OUT closes."""
		open_in = {"shift": "7PM-3:30AM", "time": datetime(2026, 9, 6, 13, 0)}
		chosen = choose_shift(datetime(2026, 9, 7, 19, 45), "OUT", [_day(), _night()], open_in)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")


class TestSupersede(unittest.TestCase):
	def test_an_older_open_ended_assignment_ends_the_day_before_the_new_one(self):
		existing = [
			{"name": "SA-1", "shift_type": "7PM-3:30AM", "start_date": date(2026, 6, 1), "end_date": None}
		]
		self.assertEqual(
			superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [("SA-1", date(2026, 8, 31))]
		)

	def test_an_assignment_already_ended_before_the_new_start_is_left_alone(self):
		existing = [
			{
				"name": "SA-1",
				"shift_type": "7PM-3:30AM",
				"start_date": date(2026, 6, 1),
				"end_date": date(2026, 8, 15),
			}
		]
		self.assertEqual(superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [])

	def test_same_shift_and_later_assignments_are_left_alone(self):
		existing = [
			{"name": "SA-1", "shift_type": "10AM-7PM", "start_date": date(2026, 6, 1), "end_date": None},
			{"name": "SA-2", "shift_type": "Night", "start_date": date(2026, 10, 1), "end_date": None},
		]
		self.assertEqual(superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [])


class TestWiring(unittest.TestCase):
	def test_the_override_uses_the_rule_and_no_longer_picks_the_nearest_start(self):
		src = (HRMS / "overrides" / "employee_checkin_override.py").read_text()
		self.assertIn("choose_shift(", src)
		self.assertNotIn("Picked closest shift", src)
		self.assertIn("def _open_in", src)

	def test_the_supersede_hook_is_registered_on_submit(self):
		hooks = (HRMS / "hooks.py").read_text()
		self.assertIn(
			'"on_submit": "hrms.overrides.shift_assignment_hooks.close_superseded_assignments"', hooks
		)
		tree = ast.parse((HRMS / "overrides" / "shift_assignment_hooks.py").read_text())
		fn = next(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef) and n.name == "close_superseded_assignments"
		)
		names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
		self.assertIn("superseded_assignments", names)


if __name__ == "__main__":
	unittest.main()
