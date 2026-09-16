"""Who owns an Attendance row is read from evidence, never from a blank tick.

`auto_attendance` was added on 1 September 2026 with default 0 and no backfill,
and ERP-mirrored rows never carry it. So every row written before that date, and
every mirrored row, reads "marked by HR by hand" to
`attendance_recovery.protected_reason`, and every automatic fix skips it (live,
15 Sep: "fixed 8, 73 need HR"; HR-EMP-00313 shows Present (HR) / Half Day (HR) /
Absent (HR) for a whole month nobody touched).

`hrms.utils.attendance_ownership` answers the question from what actually
happened to the row — its Version history, who created it, whether punches are
linked, the HR master-edit and HR-removed markers — and says UNSURE when the
evidence does not settle it. UNSURE is treated as HR's. Fail safe.

	PYTHONPATH=. python3 hrms/tests/test_attendance_ownership.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date, datetime
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_ownership as own

DAY = date(2026, 8, 12)
HR = "hr@nasty.test"
SYNC = "sync@nasty.test"


def _row(**extra):
	"""An Attendance row as `classify_row` receives it: the fields the DB wrapper reads."""
	row = frappe._dict(
		name="HR-ATT-2026-00001",
		employee="HR-EMP-00313",
		employee_name="Ria",
		attendance_date=DAY,
		status="Present",
		docstatus=1,
		auto_attendance=0,
		leave_type=None,
		leave_application=None,
		attendance_request=None,
		modify_half_day_status=0,
		synced_from_instance=None,
		working_hours=9.0,
		in_time=datetime(2026, 8, 12, 9, 0),
		out_time=datetime(2026, 8, 12, 18, 0),
		owner="Administrator",
		amended_from=None,
		punches=2,
	)
	row.update(extra)
	return row


def _version(owner, *fields):
	return frappe._dict(
		docname="HR-ATT-2026-00001",
		owner=owner,
		data=json.dumps({"changed": [[f, "old", "new"] for f in fields]}),
	)


class TestTheTruthTable(unittest.TestCase):
	"""One case per ownership signal, in the order the classifier reads them."""

	def _owner(self, row, versions=None, source=None):
		owner, reason = own.classify_row(row, versions=versions, source=source)
		self.assertTrue(reason, "every verdict names its evidence")
		return owner

	def test_a_leave_row_belongs_to_the_leave(self):
		self.assertEqual(self._owner(_row(leave_type="Annual Leave")), own.OWNER_REQUEST)
		self.assertEqual(self._owner(_row(status="On Leave")), own.OWNER_REQUEST)
		self.assertEqual(self._owner(_row(leave_application="HR-LAP-0001")), own.OWNER_REQUEST)

	def test_a_half_day_leave_belongs_to_the_leave(self):
		self.assertEqual(self._owner(_row(modify_half_day_status=1)), own.OWNER_REQUEST)

	def test_a_row_from_an_attendance_request_belongs_to_the_request(self):
		self.assertEqual(self._owner(_row(attendance_request="HR-ATR-0001")), own.OWNER_REQUEST)

	def test_a_person_changing_the_status_or_the_times_owns_the_row(self):
		for field in ("status", "in_time", "out_time", "working_hours"):
			self.assertEqual(self._owner(_row(), [_version(HR, field)]), own.OWNER_HR, field)

	def test_the_schedulers_own_version_entries_are_not_a_person(self):
		self.assertEqual(self._owner(_row(), [_version("Administrator", "status")]), own.OWNER_SYSTEM)

	def test_a_person_touching_an_unrelated_field_does_not_take_the_row(self):
		self.assertEqual(self._owner(_row(), [_version(HR, "shift")]), own.OWNER_SYSTEM)

	def test_a_row_a_person_created_with_no_punch_behind_it_is_hrs(self):
		self.assertEqual(self._owner(_row(owner=HR, punches=0)), own.OWNER_HR)

	def test_the_master_edit_marker_says_hr(self):
		self.assertEqual(self._owner(_row(), source={"hr_master_edit": True}), own.OWNER_HR)

	def test_the_hr_removed_marker_says_hr(self):
		self.assertEqual(self._owner(_row(), source={"hr_removed": True}), own.OWNER_HR)

	def test_an_amendment_a_person_made_is_hrs(self):
		self.assertEqual(self._owner(_row(owner=HR, amended_from="HR-ATT-2026-00001")), own.OWNER_HR)

	def test_an_amendment_automation_made_is_not_hrs(self):
		row = _row(owner="Administrator", amended_from="HR-ATT-2026-00001")
		self.assertEqual(self._owner(row), own.OWNER_SYSTEM)

	def test_the_hourly_job_with_punches_linked_is_system_made(self):
		self.assertEqual(self._owner(_row()), own.OWNER_SYSTEM)

	def test_a_mirrored_row_whose_erp_owner_is_a_system_user_is_system_made(self):
		row = _row(synced_from_instance="nasty-live", owner=SYNC, punches=0)
		source = {"erp_owner": "Administrator", "system_users": {SYNC}}
		self.assertEqual(self._owner(row, source=source), own.OWNER_SYSTEM)

	def test_a_mirrored_row_a_person_wrote_in_the_old_system_is_hrs(self):
		row = _row(synced_from_instance="nasty-live", owner=SYNC, punches=0)
		source = {"erp_owner": HR, "system_users": {SYNC}}
		self.assertEqual(self._owner(row, source=source), own.OWNER_HR)

	def test_a_mirrored_row_with_no_erp_side_answer_falls_back_to_who_copied_it(self):
		row = _row(synced_from_instance="nasty-live", owner="Administrator", punches=0)
		self.assertEqual(self._owner(row, source={}), own.OWNER_SYSTEM)

	def test_evidence_that_settles_nothing_reads_unsure(self):
		# a person owns it, punches are linked, no version, no marker: not provable either way
		self.assertEqual(self._owner(_row(owner=HR, punches=2)), own.OWNER_UNSURE)


class TestIsSystemOwned(unittest.TestCase):
	"""The helper other modules call instead of reading `auto_attendance`."""

	def test_a_system_made_row_with_the_tick_off_still_reads_system(self):
		self.assertTrue(own.is_system_owned(_row(auto_attendance=0)))

	def test_an_hr_row_with_the_tick_on_does_not_read_system(self):
		self.assertFalse(own.is_system_owned(_row(auto_attendance=1, owner=HR, punches=0)))

	def test_unsure_is_never_system(self):
		self.assertFalse(own.is_system_owned(_row(owner=HR, punches=2)))


class _Reads:
	"""One `frappe.get_all` stand-in that records every doctype it was asked for."""

	def __init__(self, rows=None, versions=None, punches=None, comments=None):
		self.rows = rows or []
		self.versions = versions or []
		self.punches = punches or []
		self.comments = comments or []
		self.calls = []

	def __call__(self, doctype, *args, **kwargs):
		self.calls.append(doctype)
		return {
			"Attendance": self.rows,
			"Version": self.versions,
			"Employee Checkin": self.punches,
			"Comment": self.comments,
		}.get(doctype, [])


class TestTheDatabaseWrappers(unittest.TestCase):
	def _reads(self, count=3):
		rows = [_row(name=f"ATT-{i}", employee=f"E{i}") for i in range(count)]
		return _Reads(
			rows=rows,
			versions=[
				frappe._dict(docname="ATT-0", owner=HR, data=json.dumps({"changed": [["status", 1, 2]]}))
			],
			punches=[frappe._dict(attendance="ATT-1"), frappe._dict(attendance="ATT-1")],
		)

	def test_one_window_reads_the_versions_once_for_every_row(self):
		reads = self._reads(count=25)
		with (
			patch.object(frappe, "get_all", reads),
			patch.object(own.hr_removed_day, "removed_days", return_value=set()),
		):
			out = own.classify_window(DAY, DAY)
		self.assertEqual(len(out), 25)
		self.assertEqual(reads.calls.count("Version"), 1, "the Version history is read in one batch")
		self.assertEqual(reads.calls.count("Attendance"), 1)
		self.assertEqual(reads.calls.count("Employee Checkin"), 1)

	def test_a_row_a_person_edited_comes_back_hr_owned(self):
		reads = self._reads()
		with (
			patch.object(frappe, "get_all", reads),
			patch.object(own.hr_removed_day, "removed_days", return_value=set()),
		):
			out = {r["attendance"]: r for r in own.classify_window(DAY, DAY)}
		self.assertEqual(out["ATT-0"]["owner"], own.OWNER_HR)
		self.assertEqual(out["ATT-1"]["owner"], own.OWNER_SYSTEM)
		self.assertTrue(out["ATT-1"]["would_relabel"], "system-made with the tick off is what relabel fixes")
		self.assertFalse(out["ATT-0"]["would_relabel"])

	def test_a_day_asks_for_that_employee_and_that_date_only(self):
		reads = self._reads(count=1)
		with (
			patch.object(frappe, "get_all", reads),
			patch.object(own.hr_removed_day, "removed_days", return_value=set()),
		):
			out = own.classify_day("E0", DAY)
		self.assertEqual(len(out), 1)
		self.assertEqual(out[0]["employee"], "E0")

	def test_an_hr_removed_day_is_hrs_however_the_row_reads(self):
		reads = self._reads(count=1)
		with (
			patch.object(frappe, "get_all", reads),
			patch.object(own.hr_removed_day, "removed_days", return_value={DAY}),
		):
			out = own.classify_window(DAY, DAY)
		self.assertEqual(out[0]["owner"], own.OWNER_HR)


if __name__ == "__main__":
	unittest.main()
