"""The report shows each employee-day's verdict and counts the repairable ones.

PYTHONPATH=. python3 hrms/hr/report/attendance_day_audit/test_attendance_day_audit.py
"""

import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tests"))
import _frappe_stub

_frappe_stub.install()

from hrms.hr.report.attendance_day_audit import attendance_day_audit as report
from hrms.utils import attendance_day_audit

FIXED = {
	"days": [
		{
			"employee": "HR-EMP-00012",
			"employee_name": "Nabil",
			"date": date(2026, 9, 7),
			"punches": "10:02 IN, 19:32 OUT",
			"punch_count": 2,
			"attendance": "HR-ATT-2026-00070",
			"status": "Absent",
			"working_hours": 0.0,
			"shift": "10AM-7PM",
			"repair_punches": ["A", "B"],
			"verdict": "punches-skip-stamped",
			"detail": "every punch is skip-stamped: Duplicate",
			"repair": "unskip",
		},
		{
			"employee": "HR-EMP-00013",
			"employee_name": "Mira",
			"date": date(2026, 9, 7),
			"punches": "09:00 IN, 18:00 OUT",
			"punch_count": 2,
			"attendance": "HR-ATT-2026-00071",
			"status": "Present",
			"working_hours": 9.0,
			"shift": "10AM-7PM",
			"repair_punches": [],
			"verdict": "marked",
			"detail": "HR-ATT-2026-00071 Present from 2 punch(es)",
			"repair": "",
		},
	]
}


class TestReport(unittest.TestCase):
	def setUp(self):
		patcher = patch.object(attendance_day_audit, "collect", return_value=FIXED)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_columns_and_message(self):
		columns, rows, message = report.execute({"from_date": "2026-09-01", "to_date": "2026-09-09"})
		names = [c["fieldname"] for c in columns]
		for expected in (
			"employee",
			"date",
			"punches",
			"attendance",
			"status",
			"verdict_label",
			"detail",
			"repair",
		):
			self.assertIn(expected, names)
		self.assertEqual(len(rows), 2)
		self.assertIn("2 employee-days", message)
		self.assertIn("1 repairable", message)

	def test_verdict_filter_narrows_and_labels_are_words(self):
		_c, rows, _m = report.execute(
			{"from_date": "2026-09-01", "to_date": "2026-09-09", "verdict": "punches-skip-stamped"}
		)
		self.assertEqual([r["employee"] for r in rows], ["HR-EMP-00012"])
		self.assertEqual(rows[0]["verdict_label"], "Punches skip-stamped (old failure)")


if __name__ == "__main__":
	unittest.main()
