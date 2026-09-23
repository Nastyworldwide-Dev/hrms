"""The Calendar shows every kind of day: travel, training and open requests.

Owner ruling R1, 23 Sep 2026: the key always shows every kind, plus three new
ones — Travel, Training, and Open request (approvers only: a day with a
request waiting on THEM). Managers see the TYPE of a request, never its
reason, so the open-request dot carries a date and nothing else.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_kinds.py
"""

import datetime
import pathlib
import sys
import unittest
from types import MappingProxyType
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import calendar

D = datetime.date
START, END = D(2026, 9, 1), D(2026, 9, 30)


def _site(tables: dict, doctypes=("Travel Request", "Training Event")):
	"""get_all / db.exists over in-memory tables; records the filters asked."""
	asked = []

	def get_all(doctype, filters=None, **kw):
		asked.append((doctype, filters))
		return [frappe._dict(row) for row in tables.get(doctype, [])]

	def exists(doctype, name=None, *a, **kw):
		return doctype == "DocType" and name in doctypes

	return get_all, exists, asked


class TestTravelDays(unittest.TestCase):
	def _travel(self, tables, doctypes=("Travel Request",)):
		get_all, exists, self.asked = _site(tables, doctypes)
		with (
			patch.object(frappe, "get_all", side_effect=get_all, create=True),
			patch.object(frappe.db, "exists", side_effect=exists),
		):
			return calendar._travel_days("E1", START, END)

	def test_a_trip_marks_every_day_from_departure_to_arrival(self):
		days = self._travel(
			{
				"Travel Request": [{"name": "TR-1"}],
				"Travel Itinerary": [
					{
						"parent": "TR-1",
						"departure_date": "2026-09-08 07:00:00",
						"arrival_date": "2026-09-08 09:00:00",
					},
					{
						"parent": "TR-1",
						"departure_date": "2026-09-10 18:00:00",
						"arrival_date": "2026-09-10 20:00:00",
					},
				],
			}
		)
		self.assertEqual(days, {D(2026, 9, 8), D(2026, 9, 9), D(2026, 9, 10)})

	def test_only_approved_trips_of_the_caller(self):
		self._travel({"Travel Request": []})
		filters = self.asked[0][1]
		self.assertEqual(filters["employee"], "E1")
		self.assertEqual(filters["docstatus"], 1)

	def test_a_site_without_travel_requests_has_no_travel_days(self):
		self.assertEqual(self._travel({}, doctypes=()), set())
		self.assertEqual(self.asked, [])

	def test_days_outside_the_window_are_dropped(self):
		days = self._travel(
			{
				"Travel Request": [{"name": "TR-1"}],
				"Travel Itinerary": [
					{"parent": "TR-1", "departure_date": "2026-08-30 07:00:00", "arrival_date": None},
					{"parent": "TR-1", "departure_date": "2026-09-02 07:00:00", "arrival_date": None},
				],
			}
		)
		self.assertEqual(days, {D(2026, 9, 1), D(2026, 9, 2)})


class TestTrainingDays(unittest.TestCase):
	def _training(self, tables, doctypes=("Training Event",)):
		get_all, exists, self.asked = _site(tables, doctypes)
		with (
			patch.object(frappe, "get_all", side_effect=get_all, create=True),
			patch.object(frappe.db, "exists", side_effect=exists),
		):
			return calendar._training_days("E1", START, END)

	def test_an_event_the_employee_attends_marks_its_days(self):
		days = self._training(
			{
				"Training Event Employee": [{"parent": "TE-1"}],
				"Training Event": [
					{"start_time": "2026-09-14 09:00:00", "end_time": "2026-09-15 17:00:00"},
				],
			}
		)
		self.assertEqual(days, {D(2026, 9, 14), D(2026, 9, 15)})

	def test_cancelled_events_are_not_asked_for(self):
		self._training(
			{
				"Training Event Employee": [{"parent": "TE-1"}],
				"Training Event": [],
			}
		)
		roster, events = self.asked[0][1], self.asked[1][1]
		self.assertEqual(roster["employee"], "E1")
		self.assertEqual(events["event_status"], ("!=", "Cancelled"))
		self.assertEqual(events["name"], ("in", ["TE-1"]))

	def test_no_listed_events_is_one_query(self):
		self.assertEqual(self._training({"Training Event Employee": []}), set())
		self.assertEqual(len(self.asked), 1)

	def test_a_site_without_training_events_has_no_training_days(self):
		self.assertEqual(self._training({}, doctypes=()), set())


class TestOpenDays(unittest.TestCase):
	ROWS = (
		{"doctype": "Leave Application", "name": "LA-1", "section": "yours"},
		{"doctype": "OT Request", "name": "OT-1", "section": "yours"},
		{"doctype": "Leave Application", "name": "LA-2", "section": "other"},
		{"doctype": "Expense Claim", "name": "EC-1", "section": "yours"},
		{"doctype": "Compensatory Leave Request", "name": "CL-1", "section": "yours"},
	)
	DATES = MappingProxyType(
		{
			("Leave Application", "LA-1"): ("2026-09-03", "2026-09-04"),
			("Leave Application", "LA-2"): ("2026-09-20", "2026-09-20"),
			("OT Request", "OT-1"): ("2026-09-06",),
			("Compensatory Leave Request", "CL-1"): ("2026-09-12", "2026-09-12"),
		}
	)

	def _open(self, approver=True, rows=None, boom=None):
		self.read = []

		def get_value(doctype, name, fields, **kw):
			self.read.append((doctype, name, fields))
			return self.DATES[(doctype, name)]

		waiting = {"rows": self.ROWS if rows is None else rows, "capped": False}
		with (
			patch("hrms.api.team.is_approver", return_value=approver),
			patch(
				"hrms.api.approvals_list.get_waiting_for_me",
				side_effect=boom,
				return_value=waiting,
			),
			patch.object(frappe.db, "get_value", side_effect=get_value),
		):
			return calendar._open_days(START, END)

	def test_days_covered_by_requests_waiting_on_the_caller(self):
		self.assertEqual(
			self._open(),
			{D(2026, 9, 3), D(2026, 9, 4), D(2026, 9, 6), D(2026, 9, 12)},
		)

	def test_other_teams_requests_are_not_the_callers(self):
		self.assertNotIn(D(2026, 9, 20), self._open())
		self.assertNotIn(("Leave Application", "LA-2"), [(d, n) for d, n, _ in self.read])

	def test_only_date_fields_are_read_never_the_reason(self):
		self._open()
		for _doctype, _name, fields in self.read:
			fields = [fields] if isinstance(fields, str) else list(fields)
			for field in fields:
				self.assertIn("date", field)

	def test_not_an_approver_means_no_open_days_and_no_scan(self):
		with patch("hrms.api.approvals_list.get_waiting_for_me") as scan:
			with patch("hrms.api.team.is_approver", return_value=False):
				self.assertEqual(calendar._open_days(START, END), set())
			scan.assert_not_called()

	def test_a_failing_queue_is_no_open_days_not_an_error(self):
		self.assertEqual(self._open(boom=RuntimeError("queue down")), set())


class TestFlagOrder(unittest.TestCase):
	def test_new_kinds_sit_in_their_places(self):
		self.assertEqual(
			calendar.FLAG_ORDER,
			("leave", "travel", "training", "holiday", "event", "open", "needs_you"),
		)
		self.assertEqual(calendar.MAX_DOTS, 3)

	def test_month_flags_carry_the_new_kinds(self):
		day = D(2026, 9, 8)
		with (
			patch("hrms.api.get_current_employee", return_value="E1", create=True),
			patch.object(calendar, "_window", return_value=(START, END)),
			patch.object(frappe, "get_all", return_value=[], create=True),
			patch.object(calendar, "_leave_days", return_value=set()),
			patch.object(calendar, "_holidays", return_value=set()),
			patch.object(calendar, "_event_days", return_value=set()),
			patch.object(calendar, "_needs_you_days", return_value=set()),
			patch.object(calendar, "_travel_days", return_value={day}),
			patch.object(calendar, "_training_days", return_value={day}),
			patch.object(calendar, "_open_days", return_value={day}),
		):
			out = calendar.get_month_flags("2026-09-01", "2026-09-30")
		self.assertEqual(out["flags"], {"2026-09-08": ["travel", "training", "open"]})
		self.assertEqual(out["legend"], list(calendar.FLAG_ORDER))


if __name__ == "__main__":
	unittest.main()
