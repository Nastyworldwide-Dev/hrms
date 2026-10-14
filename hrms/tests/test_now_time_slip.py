"""How late today's check-in was, for the time slip (owner, 14 Oct 2026).

The same line the day is marked late by: shift start + the shift's grace,
only when the shift marks late at all.

    PYTHONPATH=. python3 hrms/tests/test_now_time_slip.py
"""

import ast
import datetime as dt
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent.parent / "api" / "now.py"


def _lift():
	tree = ast.parse(SOURCE.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "late_minutes")
	ns = {"cint": lambda v: int(v or 0)}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), ns)
	return ns["late_minutes"]


START = dt.datetime(2026, 10, 14, 9, 0)


class TestLateMinutes(unittest.TestCase):
	def setUp(self):
		self.late = _lift()

	def test_minutes_past_the_grace(self):
		self.assertEqual(self.late(dt.datetime(2026, 10, 14, 9, 42), START, 10, True), 32)

	def test_inside_the_grace_is_not_late(self):
		self.assertEqual(self.late(dt.datetime(2026, 10, 14, 9, 10), START, 10, True), 0)

	def test_early_is_not_late(self):
		self.assertEqual(self.late(dt.datetime(2026, 10, 14, 8, 50), START, 0, True), 0)

	def test_a_shift_that_does_not_mark_late_never_offers_a_slip(self):
		self.assertEqual(self.late(dt.datetime(2026, 10, 14, 11, 0), START, 0, False), 0)

	def test_no_check_in_is_not_late(self):
		self.assertEqual(self.late(None, START, 0, True), 0)


class TestNightShift(unittest.TestCase):
	"""Review of 923609d67: a 19:00 shift checked in at 19:30 was "not late"
	once Home was opened after midnight, and its slip was looked for on the
	wrong day. The day is the check-in's own stamped shift start."""

	def test_the_slip_day_is_the_shift_start_not_today(self):
		src = SOURCE.read_text()
		body = src[src.index("def _time_slip") : src.index("def _leave_by")]
		self.assertIn('get_datetime(session["shift_start"])', body)
		self.assertIn("day = start.date()", body)
		self.assertNotIn("now.date()}", body)

	def test_late_past_midnight_is_still_late(self):
		late = _lift()
		self.assertEqual(
			late(dt.datetime(2026, 10, 13, 19, 30), dt.datetime(2026, 10, 13, 19, 0), 0, True), 30
		)


if __name__ == "__main__":
	unittest.main()
