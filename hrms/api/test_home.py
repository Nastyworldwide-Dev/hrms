"""Home's two new blocks: This week and Coming up (owner-approved Home, 23 Sep 2026).

Both are about the SESSION user's own employee only — no endpoint takes an
employee — and both always answer, so the block can say why it is empty.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_home.py
"""

import datetime
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

import hrms.api
from hrms.api import home

D = datetime.date
DT = datetime.datetime
#: Thursday 25 Sep 2026, late evening on the employee's clock. The server's
#: own clock is deliberately NOT consulted: the week is the employee's week.
THURSDAY_NIGHT = DT(2026, 9, 25, 23, 30)


def _site(tables: dict, doctypes=("Travel Request", "Training Event")):
	"""get_all / db.exists over in-memory tables; records every query."""
	asked = []

	def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
		asked.append((doctype, filters, kw))
		rows = [frappe._dict(row) for row in tables.get(doctype, [])]
		return [row[pluck] for row in rows] if pluck else rows

	def exists(doctype, name=None, *a, **kw):
		return doctype == "DocType" and name in doctypes

	return get_all, exists, asked


class _Base(unittest.TestCase):
	def run_fn(
		self, fn, tables, *, doctypes=("Travel Request", "Training Event"), overtime=0.0, holiday_list="HL-1"
	):
		get_all, exists, self.asked = _site(tables, doctypes)
		with (
			patch.object(frappe, "get_all", side_effect=get_all, create=True),
			patch.object(frappe.db, "exists", side_effect=exists),
			patch.object(hrms.api, "get_current_employee", return_value="E1", create=True),
			patch.object(home, "employee_now", return_value=THURSDAY_NIGHT) as self.clock,
			patch.object(home, "_holiday_list", return_value=holiday_list),
			patch(
				"hrms.api.requests_summary._overtime",
				return_value={"unclaimed_days": 1, "unclaimed_hours": overtime, "compensation": "Pay"},
			),
		):
			return fn()

	def filters_for(self, doctype):
		return [f for d, f, _ in self.asked if d == doctype]


class TestHomeWeek(_Base):
	def test_an_empty_week_is_zero_days_and_nothing_to_claim(self):
		out = self.run_fn(home.get_home_week, {})
		self.assertEqual(out["days_worked"], 0)
		self.assertEqual(out["overtime_hours"], 0.0)

	def test_the_week_is_monday_to_today_on_the_employees_clock(self):
		out = self.run_fn(home.get_home_week, {})
		self.clock.assert_called_with("E1")
		self.assertEqual(out["from_date"], "2026-09-21")
		self.assertEqual(out["to_date"], "2026-09-25")
		att = self.filters_for("Attendance")[0]
		self.assertEqual(att["attendance_date"], ("between", [D(2026, 9, 21), D(2026, 9, 25)]))

	def test_only_the_callers_own_submitted_present_days_are_read(self):
		self.run_fn(home.get_home_week, {})
		att = self.filters_for("Attendance")[0]
		self.assertEqual(att["employee"], "E1")
		self.assertEqual(att["docstatus"], 1)
		self.assertEqual(att["status"], ("in", ["Present", "Half Day"]))
		self.assertEqual(self.filters_for("Employee Checkin")[0]["employee"], "E1")

	def test_attendance_and_completed_pairs_count_each_date_once(self):
		out = self.run_fn(
			home.get_home_week,
			{
				"Attendance": [{"attendance_date": D(2026, 9, 21)}, {"attendance_date": D(2026, 9, 22)}],
				"Employee Checkin": [
					# Tuesday again (already counted by attendance).
					{"time": DT(2026, 9, 22, 8), "log_type": "IN"},
					{"time": DT(2026, 9, 22, 17), "log_type": "OUT"},
					# Wednesday: a completed pair, no attendance yet.
					{"time": DT(2026, 9, 23, 8), "log_type": "IN"},
					{"time": DT(2026, 9, 23, 17), "log_type": "OUT"},
					# Thursday: still in — not a completed pair.
					{"time": DT(2026, 9, 25, 8), "log_type": "IN"},
				],
			},
		)
		self.assertEqual(out["days_worked"], 3)

	def test_a_lone_out_is_not_a_day_worked(self):
		out = self.run_fn(
			home.get_home_week,
			{"Employee Checkin": [{"time": DT(2026, 9, 24, 17), "log_type": "OUT"}]},
		)
		self.assertEqual(out["days_worked"], 0)

	def test_overtime_comes_from_the_requests_summary_not_new_maths(self):
		out = self.run_fn(home.get_home_week, {}, overtime=1.5)
		self.assertEqual(out["overtime_hours"], 1.5)


class TestHomeComingUp(_Base):
	def test_nothing_booked_and_no_holiday_list(self):
		out = self.run_fn(home.get_home_coming_up, {}, holiday_list=None)
		self.assertIsNone(out["next"])
		self.assertIsNone(out["holiday"])

	def test_nothing_booked_falls_back_to_the_next_public_holiday(self):
		out = self.run_fn(
			home.get_home_coming_up,
			{"Holiday": [{"holiday_date": D(2026, 10, 20), "description": "<p>Deepavali</p>"}]},
		)
		self.assertIsNone(out["next"])
		self.assertEqual(out["holiday"], {"label": "Deepavali", "date": "2026-10-20"})
		hol = self.filters_for("Holiday")[0]
		self.assertEqual(hol["parent"], "HL-1")
		self.assertEqual(hol["weekly_off"], 0, "a Sunday is not a public holiday")
		self.assertEqual(hol["holiday_date"], (">=", D(2026, 9, 25)))

	def test_approved_leave_of_the_caller_from_today(self):
		out = self.run_fn(
			home.get_home_coming_up,
			{
				"Leave Application": [
					{"leave_type": "Annual Leave", "from_date": D(2026, 9, 29), "description": "secret"}
				]
			},
		)
		self.assertEqual(out["next"], {"kind": "leave", "label": "Annual Leave", "date": "2026-09-29"})
		leave = self.filters_for("Leave Application")[0]
		self.assertEqual(leave["employee"], "E1")
		self.assertEqual(leave["status"], "Approved")
		self.assertEqual(leave["docstatus"], 1)
		self.assertEqual(leave["from_date"], (">=", D(2026, 9, 25)))

	def test_the_earliest_of_leave_trip_and_training_wins(self):
		out = self.run_fn(
			home.get_home_coming_up,
			{
				"Leave Application": [{"leave_type": "Annual Leave", "from_date": D(2026, 10, 5)}],
				"Travel Request": [{"name": "TR-1"}],
				"Travel Itinerary": [{"departure_date": DT(2026, 10, 1, 7)}],
				"Training Event Employee": [{"parent": "TE-1"}],
				"Training Event": [{"event_name": "First aid", "start_time": DT(2026, 9, 30, 9)}],
			},
		)
		self.assertEqual(out["next"], {"kind": "training", "label": "First aid", "date": "2026-09-30"})
		self.assertEqual(self.filters_for("Travel Request")[0]["employee"], "E1")
		self.assertEqual(self.filters_for("Training Event Employee")[0]["employee"], "E1")

	def test_missing_travel_and_training_doctypes_are_skipped(self):
		out = self.run_fn(home.get_home_coming_up, {"Travel Request": [{"name": "TR-1"}]}, doctypes=())
		self.assertIsNone(out["next"])
		self.assertEqual(self.filters_for("Travel Request"), [])
		self.assertEqual(self.filters_for("Training Event Employee"), [])

	def test_never_asks_for_a_reason(self):
		self.run_fn(home.get_home_coming_up, {})
		for doctype, _filters, kw in self.asked:
			fields = kw.get("fields") or []
			for banned in ("description", "reason", "purpose_of_travel"):
				if doctype != "Holiday":
					self.assertNotIn(banned, fields, doctype)


if __name__ == "__main__":
	unittest.main()
