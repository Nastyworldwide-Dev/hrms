"""HR reads Desk request lists by person, not by ID.

HR, 15 Sep 2026, on the OT Request list: replace the employee ID with the
employee's name "for easier work for hr". Nabil: look for the same thing in the
other lists and tidy them up so they read the same way.

The rule every HR request list now follows:
  * the first column (the list's title) is the employee's name;
  * no raw employee ID column beside it — the name already says who;
  * Employee stays a standard filter, so HR can still narrow to one person;
  * hours show two decimals in the list (display only; stored figures untouched).

`in_list_view` is only the default: a saved column set (List View Settings)
replaces it site-wide, so a patch drops the ID column from saved sets too.

PYTHONPATH=. python3 hrms/tests/test_hr_lists_show_names.py
"""

import json
import pathlib
import sys
import unittest

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _frappe_stub

_frappe_stub.install()

HRMS = pathlib.Path(__file__).resolve().parent.parent

#: doctype folder -> (employee link, its name field)
REQUEST_LISTS = {
	"ot_request": ("employee", "employee_name"),
	"replacement_leave_claim": ("employee", "employee_name"),
	"employee_issue": ("employee", "employee_name"),
	"remote_checkin_request": ("employee", "employee_name"),
	"attendance_request": ("employee", "employee_name"),
	"shift_request": ("employee", "employee_name"),
	"shift_schedule_assignment": ("employee", "employee_name"),
	"compensatory_leave_request": ("employee", "employee_name"),
	"employee_advance": ("employee", "employee_name"),
	"overtime_slip": ("employee", "employee_name"),
	"shift_swap_request": ("requesting_employee", "requesting_employee_name"),
}


def _doctype(folder):
	return json.loads(next(HRMS.glob(f"**/doctype/{folder}/{folder}.json")).read_text())


def _fields(folder):
	return {f["fieldname"]: f for f in _doctype(folder)["fields"]}


class TestNameNotId(unittest.TestCase):
	def test_the_title_column_is_the_employee_name(self):
		for folder, (_, name) in REQUEST_LISTS.items():
			self.assertEqual(_doctype(folder).get("title_field"), name, folder)

	def test_no_employee_id_or_repeated_name_column(self):
		for folder, (link, name) in REQUEST_LISTS.items():
			fields = _fields(folder)
			self.assertFalse(fields[link].get("in_list_view"), f"{folder}: {link} ID column")
			self.assertFalse(fields[name].get("in_list_view"), f"{folder}: {name} repeats the title")

	def test_employee_is_still_a_filter(self):
		for folder, (link, _) in REQUEST_LISTS.items():
			self.assertTrue(_fields(folder)[link].get("in_standard_filter"), folder)

	def test_a_swap_names_the_other_employee_too(self):
		fields = _fields("shift_swap_request")
		self.assertFalse(fields["target_employee"].get("in_list_view"))
		self.assertTrue(fields["target_employee_name"].get("in_list_view"))

	def test_compensatory_leave_list_says_which_days(self):
		fields = _fields("compensatory_leave_request")
		self.assertTrue(fields["work_from_date"].get("in_list_view"))
		self.assertTrue(fields["leave_type"].get("in_list_view"))


class TestHoursReadable(unittest.TestCase):
	def test_hours_columns_show_two_decimals(self):
		for folder, field in (("ot_request", "claimed_hours"), ("attendance", "working_hours")):
			script = next(HRMS.glob(f"**/doctype/{folder}/{folder}_list.js")).read_text()
			self.assertIn("formatters", script, folder)
			self.assertIn(f"{field}:", script, folder)
			self.assertIn("format_number(value, null, 2)", script, folder)

	def test_stored_precision_is_untouched(self):
		# Pay is computed from these; only the list display is rounded.
		self.assertEqual(_fields("ot_request")["claimed_hours"].get("precision"), "9")
		self.assertEqual(_fields("attendance")["working_hours"].get("precision"), "9")


class TestSavedColumns(unittest.TestCase):
	def setUp(self):
		from hrms.patches.v16_0 import names_not_ids_in_hr_lists as patch

		self.drop = patch.drop_id_columns

	def test_drops_the_id_and_name_columns_keeps_the_rest(self):
		saved = json.dumps(
			[
				{"fieldname": "employee", "label": "Employee"},
				{"fieldname": "status", "label": "Status"},
				{"fieldname": "employee_name", "label": "Employee Name"},
			]
		)
		self.assertEqual(
			json.loads(self.drop(saved, {"employee", "employee_name"})),
			[{"fieldname": "status", "label": "Status"}],
		)

	def test_leaves_alone_what_it_cannot_or_need_not_change(self):
		self.assertIsNone(self.drop(None, {"employee"}))
		self.assertIsNone(self.drop("", {"employee"}))
		self.assertIsNone(self.drop("not json", {"employee"}))
		self.assertIsNone(self.drop(json.dumps([{"fieldname": "status"}]), {"employee"}))

	def test_never_leaves_a_list_with_no_columns(self):
		# Dropping the only saved column clears the set, so the doctype default applies.
		saved = json.dumps([{"fieldname": "employee"}])
		self.assertEqual(self.drop(saved, {"employee"}), "")

	def test_patch_registered_once(self):
		lines = (HRMS / "patches.txt").read_text().splitlines()
		self.assertEqual(
			sum(1 for line in lines if line.startswith("hrms.patches.v16_0.names_not_ids_in_hr_lists")), 1
		)


if __name__ == "__main__":
	unittest.main()
