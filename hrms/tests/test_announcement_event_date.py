"""An Event announcement carries the day it happens (owner, 27 Oct 2026: "put any event
on a certain day" on the calendar).

Before this the calendar dot sat on `publish_from` ("show from"), the day HR starts showing the
notice, so an event announced on 1 Nov for 20 Nov got its dot on 1 Nov. `event_date` is the day
itself: required when the category is Event, empty for every other category. A guarded patch
gives the Event notices already on the board an event_date (their show-from day, where their dot
already was) and clears any Property Setter that would hide or un-require the new field.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_announcement_event_date.py
"""

import json
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument

import frappe

from hrms.hr.doctype.hr_announcement import hr_announcement as ann
from hrms.patches.v16_0 import backfill_announcement_event_date as patch_module

HRMS = pathlib.Path(__file__).resolve().parents[1]


def _doc(**fields):
	"""A document whose OTHER validators are no-ops, so validate() runs only the rule under test."""
	doc = FakeDocument("HR Announcement", **fields)
	for name in (
		"set_defaults",
		"resolve_audience",
		"validate_dates",
		"enforce_single_pin",
		"clean_summary",
		"bump_version",
	):
		object.__setattr__(doc, name, lambda: None)
	object.__setattr__(
		doc, "validate_event_date", types.MethodType(ann.HRAnnouncement.validate_event_date, doc)
	)
	return doc


class EventDateRule(unittest.TestCase):
	def test_an_event_without_a_day_is_refused_in_plain_words(self):
		doc = _doc(category="Event", event_date=None)
		with self.assertRaises(frappe.ValidationError) as caught:
			ann.HRAnnouncement.validate(doc)
		self.assertIn("day", str(caught.exception).lower())

	def test_an_event_with_a_day_keeps_it(self):
		doc = _doc(category="Event", event_date="2026-11-20")
		ann.HRAnnouncement.validate(doc)
		self.assertEqual(doc.event_date, "2026-11-20")

	def test_any_other_category_drops_a_day_left_behind_by_an_earlier_edit(self):
		# HR changes Event to Notice: a stale event_date would otherwise put a dot on the calendar
		# for something that is no longer an event (and the read filters on category too).
		for category in ("Notice", "Policy", "Urgent"):
			doc = _doc(category=category, event_date="2026-11-20")
			ann.HRAnnouncement.validate(doc)
			self.assertIsNone(doc.event_date, category)

	def test_a_notice_without_a_day_is_fine(self):
		doc = _doc(category="Notice", event_date=None)
		ann.HRAnnouncement.validate(doc)
		self.assertIsNone(doc.event_date)


class EventDateField(unittest.TestCase):
	"""The Desk form: the field sits right after Category and is required only for an Event."""

	def setUp(self):
		path = HRMS / "hr" / "doctype" / "hr_announcement" / "hr_announcement.json"
		self.meta = json.loads(path.read_text())
		self.field = next(f for f in self.meta["fields"] if f["fieldname"] == "event_date")

	def test_it_is_a_date_shown_and_required_only_for_an_event(self):
		self.assertEqual(self.field["fieldtype"], "Date")
		self.assertEqual(self.field["label"], "Event date")
		self.assertEqual(self.field["depends_on"], "eval:doc.category=='Event'")
		self.assertEqual(self.field["mandatory_depends_on"], "eval:doc.category=='Event'")
		self.assertNotIn("reqd", self.field, "reqd would demand a day of every notice")

	def test_it_sits_next_to_category(self):
		order = self.meta["field_order"]
		self.assertEqual(order.index("event_date"), order.index("category") + 1)
		self.assertLess(order.index("event_date"), order.index("column_break_meta"))


class _Table:
	"""HR Announcement rows and Property Setters, answering the filter shapes the patch uses and
	refusing any other (a fake that guessed would pass a wrong filter)."""

	def __init__(self, announcements, property_setters=()):
		self.announcements = {row["name"]: dict(row) for row in announcements}
		self.property_setters = [dict(row) for row in property_setters]
		self.set_value_calls = []

	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kw):
		if doctype == "Property Setter":
			assert filters["doc_type"] == "HR Announcement" and filters["field_name"] == "event_date"
			assert filters["property"][0] == "in", filters["property"]
			wanted = filters["property"][1]
			return [p["name"] for p in self.property_setters if p["property"] in wanted]
		assert doctype == "HR Announcement", doctype
		assert set(filters) == {"category", "event_date"}, filters
		assert filters["category"] == "Event"
		assert filters["event_date"] == ("is", "not set"), filters["event_date"]
		return [
			_event_row(row)
			for row in self.announcements.values()
			if row["category"] == "Event" and not row.get("event_date")
		]

	def set_value(self, doctype, name, fieldname, value=None, update_modified=True):
		assert doctype == "HR Announcement"
		self.set_value_calls.append((name, fieldname, value, update_modified))
		self.announcements[name][fieldname] = value

	def delete(self, doctype, filters=None):
		assert doctype == "Property Setter", doctype
		assert set(filters) == {"name"} and filters["name"][0] == "in", filters
		self.property_setters = [p for p in self.property_setters if p["name"] not in filters["name"][1]]


def _event_row(row):
	return frappe._dict(name=row["name"], publish_from=row["publish_from"])


def _run(table):
	db = MagicMock()
	db.set_value.side_effect = table.set_value
	db.delete.side_effect = table.delete
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_all", side_effect=table.get_all),
		patch.object(frappe, "clear_cache", MagicMock(), create=True),
	):
		patch_module.execute()


class BackfillPatch(unittest.TestCase):
	def _board(self):
		return _Table(
			[
				{"name": "A1", "category": "Event", "publish_from": "2026-10-01", "event_date": None},
				{"name": "A2", "category": "Event", "publish_from": "2026-10-05", "event_date": "2026-11-20"},
				{"name": "A3", "category": "Notice", "publish_from": "2026-10-02", "event_date": None},
				{"name": "A4", "category": "Event", "publish_from": "2026-10-09", "event_date": None},
			]
		)

	def test_an_event_with_no_day_gets_its_show_from_day(self):
		table = self._board()
		_run(table)
		self.assertEqual(table.announcements["A1"]["event_date"], "2026-10-01")
		self.assertEqual(table.announcements["A4"]["event_date"], "2026-10-09")

	def test_it_touches_only_the_events_that_lack_a_day(self):
		table = self._board()
		_run(table)
		self.assertEqual(sorted(call[0] for call in table.set_value_calls), ["A1", "A4"])
		self.assertEqual(table.announcements["A2"]["event_date"], "2026-11-20", "HR's own day is kept")
		self.assertIsNone(table.announcements["A3"]["event_date"], "a notice is not an event")

	def test_an_event_with_no_show_from_day_is_left_alone(self):
		# Mutation probe on the backfill: an Event with no show-from day has nothing to copy, so
		# it is skipped, not written as an empty day (and not counted as filled).
		table = _Table([{"name": "A5", "category": "Event", "publish_from": None, "event_date": None}])
		_run(table)
		self.assertEqual(table.set_value_calls, [])
		self.assertIsNone(table.announcements["A5"]["event_date"])

	def test_it_does_not_bump_modified(self):
		# A backfill is not an HR edit: the board orders by `modified`, and track_changes would log
		# a version nobody made.
		table = self._board()
		_run(table)
		self.assertTrue(table.set_value_calls)
		self.assertTrue(all(call[3] is False for call in table.set_value_calls))

	def test_a_second_run_changes_nothing(self):
		table = self._board()
		_run(table)
		first = json.dumps(table.announcements, sort_keys=True)
		table.set_value_calls.clear()
		_run(table)
		self.assertEqual(table.set_value_calls, [])
		self.assertEqual(json.dumps(table.announcements, sort_keys=True), first)

	def test_a_property_setter_that_hides_or_unrequires_the_field_is_removed(self):
		# memory property-setter-shadows-doctype-json: a JSON field change alone can be shadowed.
		table = self._board()
		table.property_setters = [
			{"name": "PS-1", "property": "hidden", "value": "1"},
			{"name": "PS-2", "property": "reqd", "value": "0"},
			{"name": "PS-3", "property": "depends_on", "value": ""},
			{"name": "PS-4", "property": "mandatory_depends_on", "value": ""},
			{"name": "PS-5", "property": "label", "value": "When"},
		]
		_run(table)
		self.assertEqual([p["property"] for p in table.property_setters], ["label"])

	def test_it_runs_after_the_model_sync_so_the_column_exists(self):
		patches = (HRMS / "patches.txt").read_text()
		after_sync = patches.split("[post_model_sync]", 1)[1]
		self.assertIn("hrms.patches.v16_0.backfill_announcement_event_date", after_sync)
		self.assertEqual(patches.count("backfill_announcement_event_date"), 1)


if __name__ == "__main__":
	unittest.main()
