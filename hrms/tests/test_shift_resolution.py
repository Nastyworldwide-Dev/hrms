"""A punch belongs to the shift it was worked in, not the shift whose start is nearest.

PYTHONPATH=. python3 hrms/tests/test_shift_resolution.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

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


class TestAnOutClosesItsOwnSession(unittest.TestCase):
	"""Probed on a real site, 10 Sep 2026: a 9-6 employee who worked to 00:32
	had that check-out filed off-shift, so the day computed from the check-in
	alone and fifteen hours were recorded as none. The rule is now applied on
	every path, not only for employees holding two assignments."""

	def _doc(self, **kw):
		from unittest.mock import patch

		import hrms.overrides.employee_checkin_override as mod

		doc = mod.CustomEmployeeCheckin.__new__(mod.CustomEmployeeCheckin)
		doc.log_type = kw.get("log_type", "OUT")
		doc.attendance = kw.get("attendance")
		doc.employee = "HR-EMP-00014"
		doc.time = kw.get("time", datetime(2026, 9, 11, 0, 32))
		doc.name = "CKIN-NEW"
		doc.flags = frappe._dict(kw.get("flags") or {})
		doc.shift = doc.shift_start = doc.shift_end = None
		doc.shift_actual_start = doc.shift_actual_end = doc.offshift = None
		return doc, mod, patch

	def test_a_late_night_out_inherits_the_shift_its_in_opened(self):
		doc, mod, patch = self._doc()
		stamp = frappe._dict(
			shift="9AM-6PM",
			shift_start=datetime(2026, 9, 10, 9),
			shift_end=datetime(2026, 9, 10, 18),
			shift_actual_start=datetime(2026, 9, 10, 8),
			shift_actual_end=datetime(2026, 9, 10, 19),
		)
		with (
			patch.object(
				mod.CustomEmployeeCheckin, "_open_in", return_value={"name": "CKIN-IN", "shift": "9AM-6PM"}
			),
			patch.object(frappe.db, "get_value", return_value=stamp),
		):
			self.assertTrue(mod.CustomEmployeeCheckin._close_open_session(doc))
		self.assertEqual(doc.shift, "9AM-6PM")
		self.assertEqual(doc.shift_start, datetime(2026, 9, 10, 9))
		self.assertEqual(doc.offshift, 0)

	def test_an_in_is_never_adopted_by_this_rule(self):
		doc, mod, _patch = self._doc(log_type="IN")
		self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_no_open_in_means_the_ordinary_rules_decide(self):
		doc, mod, patch = self._doc()
		with patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_an_open_in_with_no_shift_of_its_own_settles_nothing(self):
		doc, mod, patch = self._doc()
		with patch.object(
			mod.CustomEmployeeCheckin, "_open_in", return_value={"name": "CKIN-IN", "shift": None}
		):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_a_late_checkout_searches_past_the_session_window(self):
		"""A forgotten check-out is submitted days later on purpose; bounded to
		20 hours it would be filed against the day it was typed, breaking that
		day as well as the one it belongs to."""
		doc, mod, patch = self._doc(flags={"is_late_checkout": True})
		with (
			patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None) as open_in,
			patch.object(frappe.db, "get_value", return_value=None),
		):
			mod.CustomEmployeeCheckin._close_open_session(doc)
		self.assertIs(open_in.call_args.kwargs.get("bounded"), False)

	def test_an_ordinary_out_stays_inside_the_session_window(self):
		doc, mod, patch = self._doc()
		with patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None) as open_in:
			mod.CustomEmployeeCheckin._close_open_session(doc)
		self.assertIs(open_in.call_args.kwargs.get("bounded"), True)


class TestPaidIntervals(unittest.TestCase):
	"""Early time is trimmed once, and the break deduction sees the trimmed
	span — otherwise a break configured before the shift starts is taken off
	hours that were never counted."""

	def _rule(self):
		import ast

		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		tree = ast.parse(src)
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "paid_intervals_from")
		ns = {"get_datetime": lambda v: v}
		exec(compile(ast.Module(body=[fn], type_ignores=[]), "shift_type.py", "exec"), ns)
		return ns["paid_intervals_from"]

	def test_an_early_arrival_is_trimmed_to_the_shift_start(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 7, 30), datetime(2026, 9, 10, 18, 5))], datetime(2026, 9, 10, 9)
		)
		self.assertEqual(paid, [(datetime(2026, 9, 10, 9), datetime(2026, 9, 10, 18, 5))])
		self.assertAlmostEqual(removed, 1.5)

	def test_an_interval_entirely_before_the_shift_is_dropped(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 7, 0), datetime(2026, 9, 10, 8, 0))], datetime(2026, 9, 10, 9)
		)
		self.assertEqual(paid, [])
		self.assertAlmostEqual(removed, 1.0)

	def test_a_day_that_starts_on_time_is_untouched(self):
		span = [(datetime(2026, 9, 10, 9), datetime(2026, 9, 10, 18))]
		paid, removed = self._rule()(span, datetime(2026, 9, 10, 9))
		self.assertEqual(paid, span)
		self.assertEqual(removed, 0.0)

	def test_a_night_shift_arrival_costs_its_own_quarter_hour_only(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 18, 45), datetime(2026, 9, 11, 3, 30))], datetime(2026, 9, 10, 19)
		)
		self.assertEqual(paid[0][0], datetime(2026, 9, 10, 19))
		self.assertAlmostEqual(removed, 0.25)

	def test_no_shift_start_leaves_everything_paid(self):
		span = [(datetime(2026, 9, 10, 7, 30), datetime(2026, 9, 10, 18))]
		paid, removed = self._rule()(span, None)
		self.assertEqual(paid, span)
		self.assertEqual(removed, 0.0)


class TestWiring(unittest.TestCase):
	def test_the_break_deduction_sees_the_trimmed_span(self):
		"""Trim first, then deduct breaks against what is left."""
		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		body = src[src.index("		intervals, unpaid_early = paid_intervals_from(") :]
		body = body[: body.index("		if (")]
		self.assertLess(body.index("paid_intervals_from"), body.index("_deduct_unpaid_breaks"))

	def test_the_session_rule_runs_before_any_assignment_counting(self):
		"""It must apply to the single-assignment path too — that is where the
		fifteen-hour day was being thrown away."""
		src = (HRMS / "overrides" / "employee_checkin_override.py").read_text()
		body = src[src.index("\tdef fetch_shift(self):") :]
		body = body[: body.index("\tdef _close_open_session")]
		self.assertLess(body.index("_close_open_session()"), body.index("active_assignments = "))

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
