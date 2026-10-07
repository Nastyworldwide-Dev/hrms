"""HR changes ONE roster field without re-entering the rest (owner ruling R3a, 7 Oct 2026).

Owner: HR cannot change one field (status, day type, location) on its own; one change forces others.

- `change_shift_day` (one day, still the split of A6) keeps the day's shift and location when the
  caller does not send them; an empty location sent on purpose clears it.
- `update_shift_assignment` (the whole assignment) changes only the fields the caller sent: status,
  end date, Day Type, Shift Location. A Day Type word clears the Roster Day markers inside the range
  (A2: last word wins) and is refused for a supervisor over worked days; Shift Location is not
  allow_on_submit, so it is written with db_set.

Stub tests, no bench:

	PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_roster_edit_in_place.py
"""

import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from _fake_document import FakeDocument

import frappe

from hrms.api import roster
from hrms.api.test_roster_day import _Store, _world
from hrms.utils import day_remark

_REAL_VALID_DAY_TYPE = roster._valid_day_type
DAY_TYPE_OPTIONS = "None\nWork Day\nRest Day\nOff Day\nPublic Holiday"


class _EditStore(_Store):
	"""The Roster Day store, plus Shift Locations and a range-aware worked-day lookup."""

	def __init__(self):
		super().__init__()
		self.locations = {"Lot 5", "Lot 6"}

	def exists(self, arg, filters=None):
		if arg == "Shift Location":
			return filters in self.locations
		if arg == "Attendance":
			between = filters["attendance_date"]
			if isinstance(between, list | tuple):
				lo, hi = between[1]
				return any(str(lo) <= day <= str(hi) for day in self.worked)
		return super().exists(arg, filters)

	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kwargs):
		# what `_assignments_and_worked_days` reads: the attendance days, no punches, no other assignment
		if doctype == "Attendance":
			start = str(filters["attendance_date"][1])
			return sorted(day for day in self.worked if day >= start)
		if doctype in ("Shift Assignment", "Employee Checkin"):
			return []
		return super().get_all(doctype, filters, fields, pluck, **kwargs)


def _assignment(**fields):
	"""A submitted Shift Assignment; `saves` records the whole-document saves it takes."""
	saves = []
	defaults = {
		"name": "SA-1",
		"employee": "EMP-1",
		"company": "Co A",
		"shift_type": "Day",
		"shift_location": "Lot 5",
		"status": "Active",
		"day_type": "None",
		"start_date": "2026-10-05",
		"end_date": "2026-10-16",
		"docstatus": 1,
	}
	doc = FakeDocument("Shift Assignment", flags=frappe._dict(), **{**defaults, **fields})
	object.__setattr__(
		doc, "save", lambda: saves.append((doc.status, doc.end_date, doc.day_type, doc.shift_location))
	)
	object.__setattr__(doc, "saves", saves)
	return doc


class _Base(unittest.TestCase):
	def setUp(self):
		self.store = _EditStore()
		self.doc = _assignment()
		self.created = MagicMock()
		self.logger = MagicMock()
		self.broke = MagicMock()  # break_shift: the split itself is not under test here
		self.remark = MagicMock(return_value=True)  # the real one queues a job after commit

	def world(self, **kwargs):
		stack = ExitStack()
		stack.enter_context(_world(self.store, **kwargs))
		meta = MagicMock()
		meta.get_field.return_value = frappe._dict(options=DAY_TYPE_OPTIONS)
		for obj, name, value in (
			(roster, "_valid_day_type", _REAL_VALID_DAY_TYPE),
			(frappe, "get_meta", MagicMock(return_value=meta)),
			(frappe, "get_doc", lambda *a, **k: self.doc),
			(roster, "create_shift_assignment", self.created),
			(roster, "remove_shift_day", MagicMock()),
			(roster, "logger", self.logger),
			(roster, "break_shift", self.broke),
			(day_remark, "remark_day_after_commit", self.remark),
		):
			stack.enter_context(patch.object(obj, name, value, create=True))
		return stack


class TestChangeShiftDayKeepsWhatIsNotSent(_Base):
	def change(self, *args, **kwargs):
		with self.world():
			roster.change_shift_day("SA-1", "2026-10-07", *args, **kwargs)
		self.created.assert_called_once()
		return self.created.call_args

	def test_the_location_is_kept_when_it_is_not_sent(self):
		call = self.change("Late")
		self.assertEqual(call.args[2:7], ("Late", "2026-10-07", "2026-10-07", "Active", "Lot 5"))

	def test_an_empty_location_clears_it(self):
		self.assertIsNone(self.change("Late", shift_location="").args[6])

	def test_a_null_location_clears_it_too(self):
		# the Desk dialog sends null when its Location box is emptied
		self.assertIsNone(self.change("Late", shift_location=None).args[6])

	def test_a_named_location_replaces_it(self):
		self.assertEqual(self.change("Late", shift_location="Lot 6").args[6], "Lot 6")

	def test_the_shift_is_kept_when_it_is_not_sent(self):
		call = self.change(shift_location="Lot 6")
		self.assertEqual((call.args[2], call.args[6]), ("Day", "Lot 6"))

	def test_an_empty_shift_means_keep_the_days_shift(self):
		self.assertEqual(self.change("").args[2], "Day")
		self.created.reset_mock()
		self.assertEqual(self.change(None).args[2], "Day")

	def test_a_day_type_alone_changes_nothing_else(self):
		call = self.change(day_type="Public Holiday")
		self.assertEqual((call.args[2], call.args[6]), ("Day", "Lot 5"))
		self.assertEqual(call.kwargs["day_type"], "Public Holiday")

	def test_the_day_type_is_kept_when_it_is_not_sent(self):
		self.doc.day_type = "Off Day"
		self.assertEqual(self.change("Late").kwargs["day_type"], "Off Day")

	def test_a_one_day_change_still_goes_through_the_split(self):
		# A6: Location for one day keeps the split; the marker holds Day Type only
		with self.world():
			removed = roster.remove_shift_day
			roster.change_shift_day("SA-1", "2026-10-07", "Late")
		removed.assert_called_once_with("SA-1", "2026-10-07")


class TestUpdateShiftAssignmentChangesOnlyWhatIsSent(_Base):
	def update(self, *args, user="hr", line=(), **kwargs):
		with self.world(user=user, line=line):
			roster.update_shift_assignment("SA-1", *args, **kwargs)

	def kept(self, **expected):
		"""Every field of the document not named in `expected` is what it was before."""
		before = {
			"status": "Active",
			"end_date": "2026-10-16",
			"day_type": "None",
			"shift_location": "Lot 5",
			"shift_type": "Day",
			"start_date": "2026-10-05",
		}
		for field, value in {**before, **expected}.items():
			self.assertEqual(getattr(self.doc, field), value, field)

	def test_status_only(self):
		self.update(status="Inactive")
		self.kept(status="Inactive")
		self.assertEqual(len(self.doc.saves), 1)
		self.assertEqual(self.doc.db_writes, [], "no location write")

	def test_end_date_only(self):
		self.update(end_date="2026-10-12")
		self.kept(end_date="2026-10-12")
		self.assertEqual(len(self.doc.saves), 1)

	def test_an_empty_end_date_means_open_ended(self):
		for empty in ("", None):
			self.doc.end_date = "2026-10-16"
			self.update(end_date=empty)
			self.assertIsNone(self.doc.end_date, repr(empty))

	def test_todays_desk_call_still_works(self):
		# the Desk dialog sends status + end date, positionally or by name
		self.update("Inactive", "2026-10-12")
		self.kept(status="Inactive", end_date="2026-10-12")
		self.update("Active", None)
		self.kept(status="Active", end_date=None)

	def test_day_type_only(self):
		self.update(day_type="Off Day")
		self.kept(day_type="Off Day")
		self.assertEqual(len(self.doc.saves), 1)
		self.assertEqual(self.doc.db_writes, [])

	def test_day_type_none_follows_the_calendar_again(self):
		self.doc.day_type = "Off Day"
		self.update(day_type="None")
		self.kept(day_type="None")

	def test_location_only_is_written_with_db_set_and_never_saved(self):
		self.update(shift_location="Lot 6")
		self.assertEqual(self.doc.db_writes, [("shift_location", "Lot 6")])
		self.assertEqual(self.doc.saves, [], "the document is not saved: no restamp, no validate")
		self.kept(shift_location="Lot 6")

	def test_an_empty_location_clears_it(self):
		for empty in ("", None):
			self.doc.db_writes.clear()
			self.update(shift_location=empty)
			self.assertEqual(self.doc.db_writes, [("shift_location", None)], repr(empty))

	def test_a_cancelled_or_draft_assignment_is_refused_and_nothing_is_written(self):
		# review of 29a84584a: the location path never saves, so Frappe's own
		# docstatus check never ran and a cancelled assignment was edited unseen
		for docstatus in (0, 2):
			self.doc = _assignment(docstatus=docstatus)
			with self.assertRaises(frappe.ValidationError, msg=docstatus):
				self.update(shift_location="Lot 6")
			self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))

	def test_an_unknown_location_is_refused_and_nothing_is_written(self):
		with self.assertRaises(frappe.ValidationError):
			self.update(status="Inactive", shift_location="Nowhere")
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))
		self.kept()

	def test_an_unknown_day_type_is_refused_and_nothing_is_written(self):
		for bad in ("Weekend", "off day", "None\nWork Day"):
			with self.assertRaises(frappe.ValidationError, msg=bad):
				self.update(status="Inactive", day_type=bad)
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))
		self.kept()

	def test_an_unknown_status_is_refused(self):
		for bad in ("Cancelled", ""):
			with self.assertRaises(frappe.ValidationError, msg=repr(bad)):
				self.update(status=bad)
		self.assertEqual(self.doc.saves, [])

	def test_a_call_that_sends_nothing_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.update()
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))

	def test_every_field_at_once_is_one_save_and_one_location_write(self):
		self.update(status="Inactive", end_date="2026-10-12", day_type="Rest Day", shift_location="Lot 6")
		self.kept(status="Inactive", end_date="2026-10-12", day_type="Rest Day", shift_location="Lot 6")
		self.assertEqual(len(self.doc.saves), 1)
		self.assertEqual(self.doc.db_writes, [("shift_location", "Lot 6")])

	def test_one_log_line_names_every_field_changed(self):
		self.update(status="Inactive", day_type="Rest Day", shift_location="Lot 6")
		self.logger.info.assert_called_once()
		line = self.logger.info.call_args.args[0] % self.logger.info.call_args.args[1:]
		for named in ("SA-1", "status=Inactive", "day_type=Rest Day", "shift_location=Lot 6"):
			self.assertIn(named, line)
		self.assertNotIn("end_date", line, "a field that was not sent is not in the line")

	def test_a_stranger_is_refused_before_anything_is_read_or_written(self):
		with self.assertRaises(frappe.PermissionError):
			self.update(day_type="Off Day", user="plain", line=())
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))

	def test_the_sentinel_reads_as_a_string_to_frappes_argument_check(self):
		# Frappe passes a whitelisted function only the kwargs the browser sent, and its argument
		# check adds the default's type to the annotation: a str subclass keeps `str | None` honest.
		self.assertIsInstance(roster.NOT_SENT, str)
		for name in ("status", "end_date", "day_type", "shift_location"):
			default = __import__("inspect").signature(roster.update_shift_assignment).parameters[name].default
			self.assertIs(default, roster.NOT_SENT, name)


class TestDayTypeOverTheWholeAssignment(_Base):
	def update(self, *args, user="hr", line=(), **kwargs):
		with self.world(user=user, line=line) as _:
			roster.update_shift_assignment("SA-1", *args, **kwargs)

	def test_the_markers_inside_the_range_go_and_the_rest_stay(self):
		for date in ("2026-10-04", "2026-10-06", "2026-10-10", "2026-10-16", "2026-10-17"):
			self.store.mark("EMP-1", date)
		self.store.mark("EMP-2", "2026-10-10")
		self.update(day_type="Off Day")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-04", "2026-10-17"])
		self.assertEqual(self.store.dates("EMP-2"), ["2026-10-10"], "another person's marker stays")

	def test_this_requests_cached_day_types_are_dropped(self):
		self.update(day_type="Off Day")
		self.store.forgot.assert_called()

	def test_an_open_ended_assignment_clears_every_marker_from_its_start(self):
		self.doc.end_date = None
		for date in ("2026-10-04", "2026-10-06", "2027-01-01"):
			self.store.mark("EMP-1", date)
		self.update(day_type="Off Day")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-04"])

	def test_the_markers_go_over_the_new_end_when_the_end_moves_in_the_same_call(self):
		for date in ("2026-10-06", "2026-10-14"):
			self.store.mark("EMP-1", date)
		self.update(day_type="Off Day", end_date="2026-10-10")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-14"])

	def test_no_other_field_clears_a_marker(self):
		self.store.mark("EMP-1", "2026-10-10")
		self.update(status="Inactive")
		self.update(shift_location="Lot 6")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-10"])
		self.store.forgot.assert_not_called()

	def test_a_supervisor_is_refused_when_the_range_holds_worked_days(self):
		self.store.worked = {"2026-10-08"}
		self.store.mark("EMP-1", "2026-10-10")
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.update(day_type="Off Day", user="lead", line=["EMP-1"])
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-10"], "the marker stays")

	def test_hr_may_re_type_a_range_with_worked_days(self):
		# D3 ruling: HR passes, a supervisor does not
		self.store.worked = {"2026-10-08"}
		self.update(day_type="Off Day")
		self.assertEqual(self.doc.day_type, "Off Day")

	def test_a_supervisor_may_re_type_their_own_unworked_range(self):
		self.store.worked = {"2026-10-01"}  # before the assignment starts
		self.update(day_type="Off Day", user="lead", line=["EMP-1"])
		self.assertEqual(self.doc.day_type, "Off Day")

	def test_the_worked_days_refusal_covers_the_end_the_same_call_sets(self):
		# the word is written over the NEW range: a worked day in the extension counts
		self.store.worked = {"2026-10-20"}
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.update(day_type="Off Day", end_date="2026-10-23", user="lead", line=["EMP-1"])
		self.assertEqual((self.doc.saves, self.doc.db_writes), ([], []))

	def test_cutting_the_end_over_a_worked_day_is_still_refused_for_a_supervisor(self):
		self.store.worked = {"2026-10-14"}
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.update(day_type="Off Day", end_date="2026-10-12", user="lead", line=["EMP-1"])
		self.assertEqual(self.doc.saves, [])


if __name__ == "__main__":
	unittest.main()
