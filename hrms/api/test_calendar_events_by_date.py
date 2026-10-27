"""The calendar reads an Event by the day it HAPPENS (owner, 27 Oct 2026).

Two gaps: the dot sat on `publish_from` (the day HR starts showing the notice, not the day of the
event), and only notices live today were read, so a future event showed once its notice was already
up and a past one vanished. `_visible_event_rows(reader, start, end)` reads Events by `event_date`
inside a window, behind the SAME audience fence, and the day sheet lists them as its "events".

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_events_by_date.py
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

from hrms.api import announcements, calendar

READER = frappe._dict(name="E1", company="Acme", department="Sales - A", branch="KL")
OTHER_DEPT = frappe._dict(name="E2", company="Acme", department="Ops - A", branch="KL")


def _event(name, event_date, **kw):
	return {
		"name": name,
		"title": kw.pop("title", f"Title {name}"),
		"summary": kw.pop("summary", f"Summary {name}"),
		"category": kw.pop("category", "Event"),
		"published": kw.pop("published", 1),
		"event_date": event_date,
		"publish_from": kw.pop("publish_from", "2026-10-01"),
		"publish_until": kw.pop("publish_until", "2026-10-15"),
		"audience": kw.pop("audience", "Everyone"),
		"audience_value": kw.pop("audience_value", None),
		**kw,
	}


class _Board:
	"""HR Announcement rows answering the filter shape `_visible_event_rows` sends, and refusing
	any other: a fake that guessed would pass a wrong query."""

	def __init__(self, rows):
		self.rows = rows
		self.filters = []
		self.fields = []

	def get_all(self, doctype, filters=None, fields=None, **kw):
		assert doctype == "HR Announcement", doctype
		assert set(filters) == {"published", "category", "event_date"}, filters
		assert filters["event_date"][0] == "between", filters["event_date"]
		self.filters.append(filters)
		self.fields.append(fields)
		low, high = (str(day) for day in filters["event_date"][1])
		return [
			frappe._dict({field: row.get(field) for field in fields})
			for row in self.rows
			if row["published"] == filters["published"]
			and row["category"] == filters["category"]
			and low <= str(row["event_date"]) <= high
		]


def _read(board, reader, start, end):
	with patch.object(frappe, "get_all", side_effect=board.get_all):
		return announcements._visible_event_rows(reader, start, end)


class VisibleEventRows(unittest.TestCase):
	def test_only_events_dated_inside_the_window_are_read(self):
		board = _Board(
			[
				_event("IN", "2026-10-30"),
				_event("EDGE-START", "2026-10-01"),
				_event("EDGE-END", "2026-10-31"),
				_event("BEFORE", "2026-09-30"),
				_event("AFTER", "2026-11-01"),
			]
		)
		rows = _read(board, READER, "2026-10-01", "2026-10-31")
		self.assertEqual(sorted(row.name for row in rows), ["EDGE-END", "EDGE-START", "IN"])

	def test_a_draft_or_a_non_event_is_never_read(self):
		board = _Board(
			[
				_event("LIVE", "2026-10-30"),
				_event("DRAFT", "2026-10-30", published=0),
				_event("NOTICE", "2026-10-30", category="Notice"),
			]
		)
		rows = _read(board, READER, "2026-10-01", "2026-10-31")
		self.assertEqual([row.name for row in rows], ["LIVE"])

	def test_an_event_shows_on_its_day_whether_or_not_its_notice_is_live_today(self):
		# Show-from still ahead, and a show-until long past: the calendar still has the day.
		board = _Board(
			[
				_event(
					"ANNOUNCED-LATER", "2026-10-30", publish_from="2026-12-01", publish_until="2026-12-05"
				),
				_event("NOTICE-EXPIRED", "2026-10-12", publish_from="2026-09-01", publish_until="2026-09-05"),
			]
		)
		rows = _read(board, READER, "2026-10-01", "2026-10-31")
		self.assertEqual(sorted(row.name for row in rows), ["ANNOUNCED-LATER", "NOTICE-EXPIRED"])
		for filters in board.filters:
			self.assertNotIn("publish_from", filters)
			self.assertNotIn("publish_until", filters)

	def test_the_audience_fence_is_the_boards_own(self):
		board = _Board(
			[
				_event("ALL", "2026-10-30"),
				_event("SALES", "2026-10-30", audience="Department", audience_value="Sales - A"),
				_event("OPS", "2026-10-30", audience="Department", audience_value="Ops - A"),
				_event("OTHER-CO", "2026-10-30", audience="Company", audience_value="Beta"),
				_event("KL", "2026-10-30", audience="Branch", audience_value="KL"),
				_event("NO-TARGET", "2026-10-30", audience="Department", audience_value=None),
				_event("UNKNOWN", "2026-10-30", audience="Planet", audience_value="Mars"),
			]
		)
		seen = sorted(row.name for row in _read(board, READER, "2026-10-01", "2026-10-31"))
		self.assertEqual(seen, ["ALL", "KL", "SALES"])
		other = sorted(row.name for row in _read(board, OTHER_DEPT, "2026-10-01", "2026-10-31"))
		self.assertEqual(other, ["ALL", "KL", "OPS"], "a Department notice is not another department's")

	def test_who_it_was_addressed_to_is_not_sent_back(self):
		board = _Board([_event("SALES", "2026-10-30", audience="Department", audience_value="Sales - A")])
		(row,) = _read(board, READER, "2026-10-01", "2026-10-31")
		self.assertNotIn("audience", row)
		self.assertNotIn("audience_value", row)
		self.assertEqual(
			sorted(row), ["event_date", "name", "summary", "title"], "only what the calendar draws"
		)


class EventDots(unittest.TestCase):
	def _days(self, rows, start, end, reader=READER):
		board = _Board(rows)
		with (
			patch("hrms.api.announcements._reader", return_value=reader),
			patch.object(frappe, "get_all", side_effect=board.get_all),
		):
			return calendar._event_days("E1", start, end)

	def test_the_dot_lands_on_the_event_day_not_the_show_from_day(self):
		# Announced 1 Nov for 20 Nov.
		rows = [_event("E", "2026-11-20", publish_from="2026-11-01", publish_until="2026-11-21")]
		days = self._days(rows, datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))
		self.assertEqual(days, {datetime.date(2026, 11, 20)})

	def test_a_window_that_does_not_hold_the_event_day_has_no_dot(self):
		rows = [_event("E", "2026-11-20", publish_from="2026-11-01")]
		self.assertEqual(self._days(rows, datetime.date(2026, 11, 1), datetime.date(2026, 11, 10)), set())

	def test_an_event_from_another_audience_draws_no_dot(self):
		rows = [_event("OPS", "2026-11-20", audience="Department", audience_value="Ops - A")]
		self.assertEqual(self._days(rows, datetime.date(2026, 11, 1), datetime.date(2026, 11, 30)), set())

	def test_no_board_means_no_event_dots_not_an_error(self):
		# The fail-soft rule of test_calendar_event_dot_soft.py, on the seam _event_days reads now.
		def no_table(*args, **kwargs):
			raise frappe.DoesNotExistError("DocType HR Announcement not found")

		with (
			patch("hrms.api.announcements._reader", return_value=READER),
			patch.object(frappe, "get_all", side_effect=no_table),
		):
			self.assertEqual(
				calendar._event_days("E1", datetime.date(2026, 11, 1), datetime.date(2026, 11, 30)), set()
			)

	def test_a_real_bug_in_the_board_still_fails_loudly(self):
		def bug(*args, **kwargs):
			raise KeyError("department")

		with (
			patch("hrms.api.announcements._reader", return_value=READER),
			patch.object(frappe, "get_all", side_effect=bug),
			self.assertRaises(KeyError),
		):
			calendar._event_days("E1", datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))

	def test_no_employee_means_no_dots(self):
		rows = [_event("E", "2026-11-20")]
		self.assertEqual(
			self._days(rows, datetime.date(2026, 11, 1), datetime.date(2026, 11, 30), reader=None), set()
		)


class DaySheetEvents(unittest.TestCase):
	def _sections(self, rows, reader=READER, day="2026-11-20", rows_error=None):
		board = _Board(rows)
		get_all = board.get_all if rows_error is None else rows_error
		with (
			patch("hrms.api.get_current_employee", return_value="E1", create=True),
			patch("hrms.api.team.own_team_members", return_value=[]),
			patch("hrms.api.announcements._reader", return_value=reader),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(calendar, "_my_day", return_value={}),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
		):
			return calendar.get_day(day)

	def test_the_days_events_arrive_as_name_title_summary(self):
		rows = [
			_event("A", "2026-11-20", title="Hari Raya potluck", summary="Pantry, 12:30"),
			_event("B", "2026-11-21", title="Another day"),
		]
		sections = self._sections(rows)
		self.assertEqual(
			sections["events"], [{"name": "A", "title": "Hari Raya potluck", "summary": "Pantry, 12:30"}]
		)

	def test_two_events_on_one_day_both_arrive(self):
		sections = self._sections([_event("A", "2026-11-20"), _event("B", "2026-11-20")])
		self.assertEqual(sorted(event["name"] for event in sections["events"]), ["A", "B"])

	def test_a_day_with_no_event_has_no_events_section_at_all(self):
		# A section that did not arrive renders nothing (DaySheet.vue).
		sections = self._sections([_event("A", "2026-11-21")])
		self.assertNotIn("events", sections)

	def test_an_event_for_another_audience_is_not_in_the_section(self):
		rows = [_event("OPS", "2026-11-20", audience="Department", audience_value="Ops - A")]
		self.assertNotIn("events", self._sections(rows))

	def test_the_day_asked_for_is_the_whole_window(self):
		board = _Board([])
		with (
			patch("hrms.api.get_current_employee", return_value="E1", create=True),
			patch("hrms.api.team.own_team_members", return_value=[]),
			patch("hrms.api.announcements._reader", return_value=READER),
			patch.object(frappe, "get_all", side_effect=board.get_all),
			patch.object(calendar, "_my_day", return_value={}),
			patch.object(frappe, "session", frappe._dict(user="staff@example.com")),
		):
			calendar.get_day("2026-11-20")
		(filters,) = board.filters
		self.assertEqual([str(day) for day in filters["event_date"][1]], ["2026-11-20", "2026-11-20"])

	def test_a_site_without_the_board_still_opens_the_day(self):
		def no_table(*args, **kwargs):
			raise frappe.DoesNotExistError("DocType HR Announcement not found")

		sections = self._sections([], rows_error=no_table)
		self.assertNotIn("events", sections)
		self.assertIn("me", sections)

	def test_a_real_bug_in_the_board_still_fails_loudly(self):
		def bug(*args, **kwargs):
			raise KeyError("department")

		with self.assertRaises(KeyError):
			self._sections([], rows_error=bug)


if __name__ == "__main__":
	unittest.main()


class TestOpenAnEventFromItsDay(unittest.TestCase):
	"""Owner, 27 Oct 2026: an event on someone's calendar can always be opened (still only by its
	audience). get_announcement allowed only notices live today, so tapping a future event (shown
	from later) or a past one said "That announcement is not available" from a row we drew."""

	def _open(self, name, board_rows, event_rows, reader=READER):
		doc = frappe._dict(name=name, version=1)
		with (
			patch.object(announcements, "_reader", return_value=reader),
			patch.object(
				announcements, "_visible_rows", return_value=[frappe._dict(name=n) for n in board_rows]
			),
			patch.object(
				announcements,
				"_visible_event_row",
				side_effect=lambda r, n: frappe._dict(name=n) if n in event_rows else None,
			),
			patch.object(announcements, "_record_read") as record,
			patch.object(announcements, "_confirmed", return_value=False),
			patch.object(announcements, "_payload", return_value={"name": name}),
			patch.object(frappe, "get_doc", return_value=doc),
		):
			out = announcements.get_announcement(name)
		return out, record

	def test_an_event_not_on_the_board_today_still_opens_and_is_read(self):
		out, record = self._open("EV1", board_rows=[], event_rows=["EV1"])
		self.assertEqual(out["name"], "EV1")
		record.assert_called_once_with("EV1", "E1")

	def test_outside_the_audience_it_stays_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._open("EV1", board_rows=[], event_rows=[])

	def test_the_event_fence_is_the_board_fence(self):
		row = frappe._dict(name="EV9", audience="Department", audience_value="Sales - A")
		with patch.object(frappe, "get_all", return_value=[row]):
			self.assertIsNotNone(announcements._visible_event_row(READER, "EV9"))
			self.assertIsNone(announcements._visible_event_row(OTHER_DEPT, "EV9"))
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertIsNone(announcements._visible_event_row(READER, "NOPE"))


class TestNoEmployeeNoEvents(unittest.TestCase):
	"""A login with no Employee row (a viewer, an admin) has no audience: the day sheet carries no
	events for them and never asks the board (mutation probe on _day_events)."""

	def test_no_reader_means_no_events_and_no_read(self):
		with (
			patch.object(announcements, "_reader", return_value=None),
			patch.object(announcements, "_visible_event_rows") as read,
		):
			self.assertEqual(calendar._day_events(datetime.date(2026, 10, 30)), [])
		read.assert_not_called()

	def test_a_reader_gets_the_days_events_as_title_and_summary(self):
		rows = [frappe._dict(name="EV1", title="Potluck", summary="Pantry, 12:30", event_date="2026-10-30")]
		with (
			patch.object(announcements, "_reader", return_value=READER),
			patch.object(announcements, "_visible_event_rows", return_value=rows) as read,
		):
			out = calendar._day_events(datetime.date(2026, 10, 30))
		self.assertEqual(out, [{"name": "EV1", "title": "Potluck", "summary": "Pantry, 12:30"}])
		read.assert_called_once_with(READER, datetime.date(2026, 10, 30), datetime.date(2026, 10, 30))
