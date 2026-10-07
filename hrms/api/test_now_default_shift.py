"""Home's shift line falls back to the employee's default shift.

Owner screenshot, 24 Sep 2026: Home said "No shift today" while Profile said
"Your shift: 9AM - 6PM" for the same person. `_shift_window` read only Shift
Assignment; Profile reads Employee.default_shift. HRMS itself treats the
default shift as the shift when no assignment covers the day
(`get_employee_shift(..., consider_default_shift=True)`), so Home now does too.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_now_default_shift.py
"""

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

from hrms.api import now


def _db(default_shift=None):
	def get_value(doctype, name=None, fieldname=None, **kw):
		if doctype == "Employee" and fieldname == "default_shift":
			return default_shift
		if doctype == "Shift Type":
			return {"Day": ("09:00:00", "18:00:00"), "Roster": ("22:00:00", "06:00:00")}.get(name)
		return None

	return get_value


class TestShiftFallsBackToDefault(unittest.TestCase):
	def _window(self, assignment, default_shift, rest_day=False):
		with (
			patch("hrms.utils.geofence.resolve_assignment", return_value=assignment),
			patch.object(now, "_is_rest_day", return_value=rest_day),
			patch.object(frappe.db, "get_value", side_effect=_db(default_shift), create=True),
		):
			return now._shift_window("EMP-1", "2026-09-24")

	def test_no_assignment_but_a_default_shift_is_a_shift(self):
		self.assertEqual(self._window(None, "Day"), {"shift": "Day", "start": "09:00", "end": "18:00"})

	def test_an_assignment_wins_over_the_default(self):
		roster = frappe._dict(shift_type="Roster")
		self.assertEqual(self._window(roster, "Day")["shift"], "Roster")

	def test_a_rest_day_is_not_a_default_shift_day(self):
		self.assertIsNone(self._window(None, "Day", rest_day=True))

	def test_an_assignment_on_a_rest_day_still_counts(self):
		roster = frappe._dict(shift_type="Roster")
		self.assertEqual(self._window(roster, "Day", rest_day=True)["shift"], "Roster")

	def test_neither_is_no_shift(self):
		self.assertIsNone(self._window(None, None))




class TestADayMarkedOffIsARestDay(unittest.TestCase):
	"""Owner, 7 Oct 2026 (alpha.39 follow-up): a day HR marked Off / Rest / Public holiday with no
	shift is a day off on Home and the Calendar day sheet too, not "your default shift"."""

	def _rest(self, holiday=False, marker=None):
		def get_value(doctype, filters=None, fieldname=None, **kw):
			if doctype == "Roster Day":
				return marker if filters == {"employee": "EMP-1", "date": "2026-10-08"} else None
			return None

		with (
			patch("erpnext.setup.doctype.employee.employee.is_holiday", return_value=holiday, create=True),
			patch.object(frappe.db, "get_value", side_effect=get_value, create=True),
			patch.object(frappe.db, "table_exists", return_value=True, create=True),
		):
			return now._is_rest_day("EMP-1", "2026-10-08")

	def test_a_marked_day_off_is_a_rest_day(self):
		for marker in ("Off Day", "Rest Day", "Public Holiday"):
			self.assertTrue(self._rest(marker=marker), marker)

	def test_an_unmarked_working_day_is_not(self):
		self.assertFalse(self._rest())

	def test_the_holiday_list_still_counts(self):
		self.assertTrue(self._rest(holiday=True))

if __name__ == "__main__":
	unittest.main()
