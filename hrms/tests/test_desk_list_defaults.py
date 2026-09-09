"""HR reads the Desk lists in the order the day happened, with the shift in view.

PYTHONPATH=. python3 hrms/tests/test_desk_list_defaults.py
"""

import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent


def _doctype(rel):
	return json.loads((HRMS / rel).read_text())


class TestListDefaults(unittest.TestCase):
	def test_checkins_sort_by_punch_time_newest_first_and_show_the_shift(self):
		d = _doctype("hr/doctype/employee_checkin/employee_checkin.json")
		self.assertEqual((d["sort_field"], d["sort_order"]), ("time", "DESC"))
		listed = {f["fieldname"] for f in d["fields"] if f.get("in_list_view")}
		self.assertTrue({"employee_name", "time", "log_type", "shift", "attendance"} <= listed)

	def test_attendance_sorts_by_date_newest_first_and_shows_status_shift_and_times(self):
		d = _doctype("hr/doctype/attendance/attendance.json")
		self.assertEqual((d["sort_field"], d["sort_order"]), ("attendance_date", "DESC"))
		listed = {f["fieldname"] for f in d["fields"] if f.get("in_list_view")}
		self.assertTrue(
			{"employee_name", "attendance_date", "status", "shift", "in_time", "out_time"} <= listed
		)


class TestFiltersAndSearch(unittest.TestCase):
	"""HR: "the sort is haywire and hard to identify, filters aren't much help"."""

	def test_checkins_filter_by_shift_and_by_what_stopped_a_punch_counting(self):
		d = _doctype("hr/doctype/employee_checkin/employee_checkin.json")
		filters = {f["fieldname"] for f in d["fields"] if f.get("in_standard_filter")}
		self.assertTrue({"employee", "log_type", "shift", "offshift", "skip_auto_attendance"} <= filters)
		self.assertIn("shift", d["search_fields"])

	def test_attendance_filters_by_shift_and_department(self):
		d = _doctype("hr/doctype/attendance/attendance.json")
		filters = {f["fieldname"] for f in d["fields"] if f.get("in_standard_filter")}
		self.assertTrue({"employee", "status", "shift", "department"} <= filters)
		self.assertIn("shift", d["search_fields"])


class TestSortColumnsAreIndexed(unittest.TestCase):
	"""Every list page filesorts on the sort column; an unindexed one scans."""

	def test_the_three_sort_columns_carry_an_index(self):
		for rel, field in (
			("hr/doctype/employee_checkin/employee_checkin.json", "time"),
			("hr/doctype/attendance/attendance.json", "attendance_date"),
			("hr/doctype/remote_checkin_request/remote_checkin_request.json", "checkin_time"),
		):
			d = _doctype(rel)
			with self.subTest(doctype=rel):
				self.assertEqual(d["sort_field"], field)
				column = next(f for f in d["fields"] if f["fieldname"] == field)
				self.assertEqual(column.get("search_index"), 1)


class TestIndicators(unittest.TestCase):
	def test_a_checkin_says_whether_it_counted(self):
		js = (HRMS / "hr/doctype/employee_checkin/employee_checkin_list.js").read_text()
		for state in ("Off-Shift", "Rejected", "Skipped", "Awaiting approval", "Counted", "Not counted yet"):
			self.assertIn(state, js)
		# the list only loads what it shows or is told to add
		for field in ("skip_auto_attendance", "attendance", "shift", "remote_approval_status"):
			self.assertIn(f'"{field}"', js.split("get_indicator")[0])

	def test_attendance_carries_its_shift_and_owner_into_the_list(self):
		js = (HRMS / "hr/doctype/attendance/attendance_list.js").read_text()
		head = js.split("get_indicator")[0]
		for field in ("shift", "auto_attendance", "working_hours"):
			self.assertIn(f'"{field}"', head)


if __name__ == "__main__":
	unittest.main()
