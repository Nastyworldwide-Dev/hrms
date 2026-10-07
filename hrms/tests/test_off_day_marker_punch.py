"""A punch on a day marked Off with no shift is overtime (alpha.39 ruling R2a, plan A3).

HR marks a day Off with no Shift Assignment (a "Roster Day" marker). A punch that
day takes the person's Employee.default_shift and, because the marker makes the
day non-normal, stamps as off-day work (flat 2x overtime). A person with no
assignment AND no default shift has no shift times to price against: the punch
stays off-shift and the reason is logged.

Stub-only: the real `_stamp_nonworking_day_shift` and the real `_classify_day`
run; only the database reads are faked.

	PYTHONPATH=. python3 hrms/tests/test_off_day_marker_punch.py
"""

import datetime as dt
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.employee_checkin import employee_checkin as ec
from hrms.utils import ot_calculation as ot

EMP = "EMP-0001"
DAY = dt.date(2026, 10, 8)  # a Thursday, a plain workday on the calendar
PUNCH = dt.datetime(2026, 10, 8, 20, 0)  # outside a 9-6 shift window


def _punch():
	return SimpleNamespace(employee=EMP, time=PUNCH, log_type="IN", attendance=None, flags=SimpleNamespace())


def _stamp(marker, default_shift):
	"""Run the real stamp with no Shift Assignment, a marker (or none) and a default shift."""
	frappe.flags = frappe._dict()
	punch = _punch()

	def get_value(doctype, filters, field=None, *a, **kw):
		if doctype == "Roster Day":
			return marker if filters == {"employee": EMP, "date": str(DAY)} else None
		if doctype == "Employee":
			return default_shift
		return None

	shift_type = SimpleNamespace(
		start_time=dt.timedelta(hours=9),
		end_time=dt.timedelta(hours=18),
		begin_check_in_before_shift_start_time=60,
		allow_check_out_after_shift_end_time=60,
	)
	with (
		patch.object(frappe, "get_all", return_value=[]),
		patch.object(frappe.db, "get_value", side_effect=get_value),
		patch.object(frappe.db, "table_exists", return_value=True),
		patch.object(frappe, "get_cached_doc", return_value=shift_type),
		patch.object(ot, "_calendar_day_type", return_value="normal"),
		patch.object(ec.logger, "info") as logged,
	):
		stamped = ec.EmployeeCheckin._stamp_nonworking_day_shift(punch)
	return stamped, punch, logged


class TestOffDayMarkerPunch(unittest.TestCase):
	def test_a_punch_on_a_marked_off_day_stamps_the_default_shift_as_overtime(self):
		stamped, punch, _logged = _stamp("Off Day", "9-6")
		self.assertTrue(stamped)
		self.assertEqual(punch.shift, "9-6")
		self.assertEqual(punch.offshift, 0)
		self.assertEqual(punch.shift_start, dt.datetime(2026, 10, 8, 9, 0))

	def test_the_same_punch_with_no_marker_stays_off_shift(self):
		stamped, punch, _logged = _stamp(None, "9-6")
		self.assertFalse(stamped)
		self.assertFalse(hasattr(punch, "shift"))

	def test_no_assignment_and_no_default_shift_stays_off_shift_and_says_why(self):
		stamped, punch, logged = _stamp("Off Day", None)
		self.assertFalse(stamped)
		self.assertFalse(hasattr(punch, "shift"))
		self.assertIn("no shift on the date", " ".join(str(c.args[0]) for c in logged.call_args_list))


if __name__ == "__main__":
	unittest.main()
