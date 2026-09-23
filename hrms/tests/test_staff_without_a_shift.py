"""Staff Without A Shift — who cannot earn rest-day or holiday overtime.

Owner ruling, 23 Sep 2026: staff with no shift at all get a warning so HR
can set one; the system does not invent a rate. A punch with no shift is
stored off-shift and never reaches overtime (5f9cb5d33 covers only staff who
HAVE a shift). This report lists Active employees with neither an Active
assignment covering today nor a default shift. Fenced like every HR report;
HR Manager and System Manager only. Nothing here writes.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_staff_without_a_shift.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.staff_without_a_shift import staff_without_a_shift as report

REPORT_DIR = pathlib.Path(__file__).resolve().parents[1] / "hr" / "report" / "staff_without_a_shift"

PEOPLE = [
	frappe._dict(name="E1", employee_name="Ann", company="Co A", department="Sales - A", default_shift=None),
	frappe._dict(name="E2", employee_name="Bob", company="Co A", department="Ops - A", default_shift="Day"),
	frappe._dict(name="E3", employee_name="Cy", company="Co B", department=None, default_shift=None),
]


def _run(fence=(), assigned=("E3",), filters=None):
	calls = {}

	def get_all(doctype, filters=None, **kw):
		calls[doctype] = filters
		if doctype == "Employee":
			companies = (filters or {}).get("company")
			rows = PEOPLE
			if companies:
				rows = [p for p in PEOPLE if p.company in companies[1]]
			return rows
		if doctype == "Shift Assignment":
			return [frappe._dict(employee=e) for e in assigned]
		return []

	with (
		patch.object(report.frappe, "get_all", side_effect=get_all),
		patch.object(report, "fenced_companies", return_value=list(fence)),
		patch.object(report, "today", return_value="2026-09-23"),
	):
		columns, rows = report.execute(filters or {})
	return columns, rows, calls


class TestStaffWithoutAShift(unittest.TestCase):
	def test_only_people_with_neither_assignment_nor_default_are_listed(self):
		_, rows, _ = _run()
		self.assertEqual([r["employee"] for r in rows], ["E1"])

	def test_each_row_says_what_it_costs_and_what_to_do(self):
		_, rows, _ = _run()
		self.assertIn("overtime on rest days and public holidays cannot be counted", rows[0]["why"])
		self.assertIn("default shift", rows[0]["why"])

	def test_department_reads_as_people_say_it(self):
		_, rows, _ = _run()
		self.assertEqual(rows[0]["department"], "Sales")

	def test_the_company_fence_reaches_the_query(self):
		_, rows, calls = _run(fence=["Co B"], assigned=())
		self.assertEqual(calls["Employee"]["company"], ("in", ["Co B"]))
		self.assertEqual([r["employee"] for r in rows], ["E3"])

	def test_assignments_are_read_for_today_only_active_and_submitted(self):
		_, _, calls = _run()
		f = calls["Shift Assignment"]
		self.assertEqual(f["status"], "Active")
		self.assertEqual(f["docstatus"], 1)
		self.assertEqual(f["start_date"], ["<=", "2026-09-23"])

	def test_hr_only(self):
		spec = json.loads((REPORT_DIR / "staff_without_a_shift.json").read_text())
		self.assertEqual({r["role"] for r in spec["roles"]}, {"HR Manager", "System Manager"})
		self.assertEqual(spec["report_type"], "Script Report")
		self.assertEqual(spec["ref_doctype"], "Employee")


if __name__ == "__main__":
	unittest.main()
