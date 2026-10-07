"""A Roster Day is a day off with no shift, never a work day (owner, 7 Oct 2026).

set_day_type refuses Work Day, but Desk writes the doctype directly, so the
doctype itself must hold the rule: its options and its validate.

	PYTHONPATH=. python3 hrms/hr/doctype/roster_day/test_roster_day.py
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.roster_day import roster_day

META = json.loads((pathlib.Path(__file__).parent / "roster_day.json").read_text())


def _validate(day_type):
	doc = roster_day.RosterDay.__new__(roster_day.RosterDay)
	object.__setattr__(doc, "__dict__", {"day_type": day_type, "doctype": "Roster Day"})
	roster_day.RosterDay.validate(doc)


class TestRosterDayIsNeverAWorkDay(unittest.TestCase):
	def test_the_options_are_the_three_days_off(self):
		field = next(f for f in META["fields"] if f["fieldname"] == "day_type")
		self.assertEqual(field["options"].split("\n"), list(roster_day.NO_SHIFT_DAY_TYPES))
		self.assertNotIn("Work Day", roster_day.NO_SHIFT_DAY_TYPES)

	def test_validate_refuses_work_day(self):
		with self.assertRaises(frappe.ValidationError):
			_validate("Work Day")

	def test_validate_accepts_each_day_off(self):
		for day_type in ("Off Day", "Rest Day", "Public Holiday"):
			_validate(day_type)

	def test_the_api_reads_the_same_list(self):
		from hrms.api import roster

		self.assertIs(roster.NO_SHIFT_DAY_TYPES, roster_day.NO_SHIFT_DAY_TYPES)


if __name__ == "__main__":
	unittest.main()
