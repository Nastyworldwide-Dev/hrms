"""HR changes a person's shift from a date (owner, 5 Oct 2026).

HR could not move someone from a 9-6 shift to a 10-7 one: the old assignment
cannot be cancelled once punches exist ("linked to Employee Checkin"), and a
submitted assignment keeps no editable shift. The way that works — end the old
one the day before, add the new from the date — was hidden and two steps.

`plan_change` is the whole rule as a pure function: given the person's
assignments and the date, what to end, what to remove, what to create. The
roster endpoint only applies it.

	PYTHONPATH=. python3 hrms/utils/test_shift_change.py
"""

import pathlib
import sys
import unittest
import unittest.mock
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils.shift_change import ShiftChangeRefused, plan_change

FROM = date(2026, 10, 12)  # a Monday


def row(name, shift, start, end=None):
	return {"name": name, "shift_type": shift, "start_date": start, "end_date": end}


class TestPlanChange(unittest.TestCase):
	def test_an_open_assignment_that_started_earlier_ends_the_day_before(self):
		plan = plan_change([row("A", "9-6", date(2026, 9, 1))], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.end, [("A", date(2026, 10, 11))])
		self.assertEqual(plan.remove, [])

	def test_the_new_shift_starts_on_the_date_for_every_day(self):
		plan = plan_change([row("A", "9-6", date(2026, 9, 1))], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.create, [("10-7", None)])
		self.assertEqual(plan.start, FROM)

	def test_days_before_the_date_are_never_touched(self):
		plan = plan_change(
			[row("A", "9-6", date(2026, 9, 1), date(2026, 10, 5))], FROM, [("10-7", None)], worked_days=[]
		)
		self.assertEqual(plan.end, [])
		self.assertEqual(plan.remove, [])

	def test_an_assignment_that_starts_on_or_after_the_date_is_removed(self):
		plan = plan_change(
			[row("A", "9-6", date(2026, 9, 1)), row("B", "9-6", date(2026, 10, 12), date(2026, 10, 30))],
			FROM,
			[("10-7", None)],
			worked_days=[],
		)
		self.assertEqual(plan.end, [("A", date(2026, 10, 11))])
		self.assertEqual(plan.remove, ["B"])

	def test_an_assignment_ending_before_the_date_is_left_alone(self):
		plan = plan_change(
			[row("A", "9-6", date(2026, 9, 1), date(2026, 10, 11))], FROM, [("10-7", None)], worked_days=[]
		)
		self.assertEqual(plan.end, [])

	def test_a_worked_day_from_the_date_refuses_and_names_the_day(self):
		with self.assertRaises(ShiftChangeRefused) as caught:
			plan_change(
				[row("A", "9-6", date(2026, 9, 1))],
				FROM,
				[("10-7", None)],
				worked_days=[date(2026, 10, 14)],
			)
		self.assertIn("2026-10-14", str(caught.exception))

	def test_worked_days_before_the_date_do_not_block(self):
		plan = plan_change(
			[row("A", "9-6", date(2026, 9, 1))], FROM, [("10-7", None)], worked_days=[date(2026, 10, 1)]
		)
		self.assertEqual(plan.end, [("A", date(2026, 10, 11))])

	def test_two_shifts_on_different_weekdays_make_two_creations(self):
		days = [("10-7", ["Monday", "Tuesday", "Wednesday", "Thursday"]), ("10-4", ["Friday"])]
		plan = plan_change([row("A", "9-6", date(2026, 9, 1))], FROM, days, worked_days=[])
		self.assertEqual([shift for shift, _days in plan.create], ["10-7", "10-4"])
		self.assertEqual(plan.create[1][1], ["Friday"])

	def test_one_weekday_on_two_shifts_is_refused(self):
		with self.assertRaises(ShiftChangeRefused):
			plan_change(
				[row("A", "9-6", date(2026, 9, 1))],
				FROM,
				[("10-7", ["Monday", "Friday"]), ("10-4", ["Friday"])],
				worked_days=[],
			)

	def test_an_every_day_shift_beside_another_shift_is_refused(self):
		with self.assertRaises(ShiftChangeRefused):
			plan_change(
				[row("A", "9-6", date(2026, 9, 1))], FROM, [("10-7", None), ("10-4", ["Friday"])], worked_days=[]
			)

	def test_a_mirrored_assignment_is_never_ended_or_removed(self):
		# rows the old ERP owns (synced_from_instance) are single-writer: refuse, never edit
		mirrored = dict(row("M", "9-6", date(2026, 9, 1)), synced_from_instance="old-erp")
		with self.assertRaises(ShiftChangeRefused) as caught:
			plan_change([mirrored], FROM, [("10-7", None)], worked_days=[])
		self.assertIn("old ERP", str(caught.exception))

	def test_a_mirrored_assignment_that_ended_before_the_date_is_not_in_the_way(self):
		mirrored = dict(row("M", "9-6", date(2026, 9, 1), date(2026, 10, 5)), synced_from_instance="old-erp")
		plan = plan_change([mirrored], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.end, [])

	def test_the_day_type_comes_only_from_the_assignment_being_ended(self):
		# reviewer 5 Oct: a future one-day "Off Day" override (removed by the change) must not
		# become the Day Type of every new assignment
		ended = dict(row("A", "9-6", date(2026, 9, 1)), day_type="None")
		override = dict(row("O", "9-6", date(2026, 10, 20), date(2026, 10, 20)), day_type="Off Day")
		plan = plan_change([ended, override], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.day_type, None)
		self.assertEqual(plan.remove, ["O"])

	def test_a_day_type_set_on_the_ended_assignment_carries_over(self):
		ended = dict(row("A", "9-6", date(2026, 9, 1)), day_type="Work Day")
		plan = plan_change([ended], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.day_type, "Work Day")

	def test_two_ended_assignments_that_disagree_carry_nothing(self):
		a = dict(row("A", "9-6", date(2026, 9, 1)), day_type="Work Day")
		b = dict(row("B", "8-5", date(2026, 9, 2)), day_type="Off Day")
		plan = plan_change([a, b], FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.day_type, None)

	def test_no_new_shift_is_refused(self):
		with self.assertRaises(ShiftChangeRefused):
			plan_change([row("A", "9-6", date(2026, 9, 1))], FROM, [], worked_days=[])

	def test_an_unknown_weekday_is_refused(self):
		with self.assertRaises(ShiftChangeRefused):
			plan_change([row("A", "9-6", date(2026, 9, 1))], FROM, [("10-7", ["Funday"])], worked_days=[])

	def test_running_it_again_after_it_was_applied_changes_nothing_more(self):
		# after the first run A ends 11 Oct and the new one starts 12 Oct on the same shift
		after = [row("A", "9-6", date(2026, 9, 1), date(2026, 10, 11)), row("N", "10-7", date(2026, 10, 12))]
		plan = plan_change(after, FROM, [("10-7", None)], worked_days=[])
		self.assertEqual(plan.end, [])
		self.assertEqual(plan.remove, ["N"])  # the same shift is re-created, never doubled
		self.assertEqual(plan.create, [("10-7", None)])



class TestTheEndpointReadsWhatWasWorked(unittest.TestCase):
	"""change_shift_from must hand plan_change the days that carry punches or
	attendance. Mutation probe, 5 Oct 2026: breaking that read left every test
	green, so the refusal that protects past days was untested."""

	def _run(self, attendance=(), punches=(), assignments=None, stamped=(), shifts=None, calls=None):
		from unittest.mock import patch

		from hrms.api import roster

		assignments = assignments or [
			_frappe_stub._Dict(
				name="A", shift_type="9-6", start_date=date(2026, 9, 1), end_date=None, day_type=None
			)
		]

		def keep(row, or_filters):
			# the database's own reading of or_filters: any one clause admits the row
			def admits(field, op, value):
				have = row[field]
				if (op, value) == ("is", "not set"):
					return have is None
				compare = {">=": lambda a, b: a >= b, "<": lambda a, b: a < b}[op]
				return have is not None and compare(have, value)

			return not or_filters or any(admits(*clause) for clause in or_filters)

		def get_all(doctype, *args, **kwargs):
			if calls is not None:
				calls.append((doctype, args, kwargs))
			if doctype == "Employee Checkin" and "shift_start" in str(kwargs.get("filters")):
				# the read for punches stamped to a shift day: answers only for a window that
				# really reaches the change date (a broken filter that asks for 1900 gets nothing)
				window = kwargs["filters"]["shift_start"]
				return [m for m in stamped if window[0] == ">=" and str(m) >= str(window[1])]
			return {
				"Shift Assignment": [row for row in assignments if keep(row, kwargs.get("or_filters"))],
				"Attendance": list(attendance),
				"Employee Checkin": list(punches),
				"Shift Schedule Assignment": [],
			}[doctype]

		fake_doc = unittest.mock.MagicMock()
		with (
			patch.object(roster, "_ensure_can_roster_employee"),
			patch("hrms.hr.utils.sees_all_employee_data", return_value=True),
			patch.object(roster.frappe, "get_all", side_effect=get_all),
			patch.object(roster.frappe, "get_doc", return_value=fake_doc),
			patch.object(roster.frappe, "db") as db,
			patch.object(roster, "create_shift_assignment") as create,
			patch.object(roster, "_remove_assignment"),
		):
			db.exists.return_value = True
			db.get_value.return_value = "Co"
			result = roster.change_shift_from(
				"EMP-1", "2026-10-12", [{"shift_type": "10-7"}] if shifts is None else shifts
			)
		return result, fake_doc, create

	def test_a_day_with_attendance_refuses(self):
		with self.assertRaises(Exception) as caught:
			self._run(attendance=[date(2026, 10, 14)])
		self.assertIn("2026-10-14", str(caught.exception))

	def test_a_day_with_a_punch_refuses(self):
		from datetime import datetime

		with self.assertRaises(Exception) as caught:
			self._run(punches=[datetime(2026, 10, 15, 9, 1)])
		self.assertIn("2026-10-15", str(caught.exception))

	def test_an_assignment_that_already_ended_is_not_touched(self):
		finished = _frappe_stub._Dict(
			name="OLD", shift_type="8-5", start_date=date(2026, 8, 1), end_date=date(2026, 9, 30), day_type=None
		)
		open_one = _frappe_stub._Dict(
			name="A", shift_type="9-6", start_date=date(2026, 9, 1), end_date=None, day_type=None
		)
		result, _doc, _create = self._run(assignments=[finished, open_one])
		self.assertEqual(result["ended"], 1)

	def test_a_dated_assignment_running_past_the_date_ends_the_day_before(self):
		dated = _frappe_stub._Dict(
			name="D", shift_type="9-6", start_date=date(2026, 9, 1), end_date=date(2026, 11, 30), day_type=None
		)
		result, doc, _create = self._run(assignments=[dated])
		self.assertEqual(result["ended"], 1)
		self.assertEqual(doc.end_date, date(2026, 10, 11))

	def test_a_punch_stamped_to_a_shift_day_on_the_date_refuses_even_if_its_clock_day_is_earlier(self):
		from datetime import datetime

		with self.assertRaises(Exception) as caught:
			self._run(stamped=[datetime(2026, 10, 12, 8, 30)])
		self.assertIn("2026-10-12", str(caught.exception))

	def test_only_schedules_this_site_owns_are_switched_off(self):
		calls = []
		self._run(calls=calls)
		schedule_filters = [a[0] for doctype, a, kw in calls if doctype == "Shift Schedule Assignment"]
		self.assertEqual(len(schedule_filters), 1)
		self.assertEqual(schedule_filters[0]["synced_from_instance"], ["is", "not set"])
		self.assertEqual(schedule_filters[0]["enabled"], 1)

	def test_a_malformed_shifts_value_is_a_plain_refusal(self):
		with self.assertRaises(Exception) as caught:
			self._run(shifts="not json")
		self.assertNotIn("JSONDecodeError", type(caught.exception).__name__)

	def test_the_new_assignment_takes_the_day_type_of_the_one_it_ends(self):
		ended = _frappe_stub._Dict(
			name="A", shift_type="9-6", start_date=date(2026, 9, 1), end_date=None, day_type="Work Day"
		)
		override = _frappe_stub._Dict(
			name="O", shift_type="9-6", start_date=date(2026, 10, 20), end_date=date(2026, 10, 20), day_type="Off Day"
		)
		_result, _doc, create = self._run(assignments=[ended, override])
		self.assertEqual(create.call_args.kwargs["day_type"], "Work Day")

	def test_an_open_ended_assignment_is_the_one_that_ends(self):
		result, doc, _create = self._run()
		self.assertEqual(result["ended"], 1)
		self.assertEqual(doc.end_date, date(2026, 10, 11))

	def test_with_nothing_worked_the_old_ends_and_the_new_is_created(self):
		result, doc, create = self._run()
		self.assertEqual(result, {"ended": 1, "removed": 0, "created": 1})
		self.assertEqual(doc.end_date, date(2026, 10, 11))
		self.assertEqual(create.call_args.args[2:5], ("10-7", date(2026, 10, 12), None))

if __name__ == "__main__":
	unittest.main()
