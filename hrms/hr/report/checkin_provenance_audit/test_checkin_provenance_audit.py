"""The audit report shows who really punched and what recovery would do.

PYTHONPATH=. python3 hrms/hr/report/checkin_provenance_audit/test_checkin_provenance_audit.py
"""

import pathlib
import sys
import unittest
from datetime import date, datetime
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tests"))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.hr.report.checkin_provenance_audit import checkin_provenance_audit as report
from hrms.sync import checkin_recovery

FIXED = {
	"rows": [
		{
			"name": "EMP-CKIN-09-2026-000007",
			"kind": checkin_recovery.OVERWRITTEN,
			"reason": "created by another employee's user",
			"synced_from_instance": "Nasty-Live",
			"employee": "HR-EMP-00301",
			"time": datetime(2026, 9, 4, 8, 41, 5),
			"log_type": "IN",
			"owner": "nabil@nasty.test",
			"creation": datetime(2026, 9, 4, 9, 2, 11),
		},
		{
			"name": "EMP-CKIN-09-2026-000040",
			"kind": checkin_recovery.LOCAL,
			"reason": "",
			"synced_from_instance": None,
			"employee": "HR-EMP-00012",
			"time": datetime(2026, 9, 7, 9, 0, 0),
			"log_type": "IN",
			"owner": "nabil@nasty.test",
			"creation": datetime(2026, 9, 7, 9, 0, 0),
		},
	],
	"plan": [
		{
			"source_name": "EMP-CKIN-09-2026-000007",
			"stamped_from": "Nasty-Live",
			"employee": "HR-EMP-00012",
			"time": datetime(2026, 9, 4, 9, 2, 11),
			"log_type": "IN",
			"confidence": "inferred",
			"action": "insert",
		}
	],
	"attendance": {
		("HR-EMP-00012", date(2026, 9, 4)): frappe._dict(
			name="HR-ATT-2026-00010",
			status="Absent",
			working_hours=0.0,
			auto_attendance=1,
			synced_from_instance=None,
		)
	},
}


class TestReport(unittest.TestCase):
	def setUp(self):
		patcher = patch.object(checkin_recovery, "collect", return_value=FIXED)
		self.collect = patcher.start()
		self.addCleanup(patcher.stop)

	def test_columns_name_the_truth_beside_what_is_shown(self):
		columns, _rows, _message = report.execute({"from_date": "2026-09-01", "to_date": "2026-09-09"})
		names = [c["fieldname"] for c in columns]
		for expected in (
			"employee",
			"time",
			"true_employee",
			"true_time",
			"true_log_type",
			"planned_action",
			"attendance_status",
		):
			self.assertIn(expected, names)

	def test_default_kind_shows_only_overwritten_rows_with_the_recovered_truth(self):
		_columns, rows, message = report.execute({"from_date": "2026-09-01", "to_date": "2026-09-09"})
		self.assertEqual([r["name"] for r in rows], ["EMP-CKIN-09-2026-000007"])
		row = rows[0]
		self.assertEqual(row["employee"], "HR-EMP-00301")
		self.assertEqual(row["true_employee"], "HR-EMP-00012")
		self.assertEqual(row["true_time"], datetime(2026, 9, 4, 9, 2, 11))
		self.assertEqual(row["planned_action"], "insert")
		self.assertEqual(row["attendance"], "HR-ATT-2026-00010")
		self.assertEqual(row["attendance_status"], "Absent")
		self.assertEqual(row["attendance_source"], "job")
		self.assertIn("Overwritten 1", message)
		self.assertIn("insert 1", message)

	def test_all_shows_local_rows_too(self):
		_columns, rows, _message = report.execute(
			{"from_date": "2026-09-01", "to_date": "2026-09-09", "kind": "All"}
		)
		self.assertEqual(len(rows), 2)
		local = next(r for r in rows if r["kind"] == checkin_recovery.LOCAL)
		self.assertEqual(local["true_employee"], "HR-EMP-00012")
		self.assertEqual(local["planned_action"], "")

	def test_the_employee_filter_reaches_collect(self):
		report.execute({"from_date": "2026-09-01", "to_date": "2026-09-09", "employee": "HR-EMP-00012"})
		self.collect.assert_called_once_with("2026-09-01", "2026-09-09", "HR-EMP-00012")


if __name__ == "__main__":
	unittest.main()
