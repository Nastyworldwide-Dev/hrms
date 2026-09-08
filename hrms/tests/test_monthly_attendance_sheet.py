"""The Monthly Attendance Sheet draws rows, summary and chart from ONE authorized population.

360 audit (Desk reports): the sheet took the requested company (plus its
descendants) at face value — no company fence, no native Employee row
restrictions — and built the attendance map for the whole company before the
employee list existed, so the chart and the summary counted people the caller
was never allowed to see. Now the employee population is resolved first
(company fence intersected with the requested companies, the native Employee
match conditions applied), and every attendance query is restricted to it.

The chart also lost every worked half-day: attendance records label half days
"Half Day/Other Half Present|Absent" while the chart only counted the bare
"Half Day". Both variants now count — the worked half as present, the other
half by its recorded status.

Bench-free: the query builder runs in memory (_qb_stub); the fence and the
native match conditions are the boundaries.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_monthly_attendance_sheet.py
"""

import sys
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub
import _qb_stub

_frappe_stub.install()
_erpnext_stub.install()
_qb_stub.install()
import frappe

from hrms.hr.report.monthly_attendance_sheet import monthly_attendance_sheet as report
from hrms.utils import report_scope

A, B, SUB = "Company A", "Company B", "Company A Sub"
D1, D2 = date(2026, 8, 3), date(2026, 8, 4)


def _getdate(value, parse_day_first=False):
	if isinstance(value, date):
		return value
	if parse_day_first:  # the chart's column keys are dd-mm-YYYY
		day, month, year = value.split("-")
		return date(int(year), int(month), int(day))
	return date.fromisoformat(str(value)[:10])


def _date_range(start, end):
	start, end = _getdate(start), _getdate(end)
	return [str(start + timedelta(days=i)) for i in range((end - start).days + 1)]


def employee(name, company, department="Ops"):
	return dict(
		name=name,
		employee_name=name.title(),
		designation=None,
		grade=None,
		department=department,
		branch=None,
		company=company,
		holiday_list=None,
		date_of_joining=date(2020, 1, 1),
	)


def attendance(employee, company, day, status, other_half=None, shift="Day"):
	return dict(
		name=f"ATT-{employee}-{day}",
		employee=employee,
		company=company,
		attendance_date=day,
		status=status,
		half_day_status=other_half,
		shift=shift,
		docstatus=1,
		leave_type=None,
		late_entry=0,
		early_exit=0,
	)


TABLES = {
	"Employee": [
		employee("alice", A),
		employee("amir", A, "Sales"),
		employee("sam", SUB),
		employee("bob", B),
	],
	"Attendance": [
		attendance("alice", A, D1, "Present"),
		attendance("alice", A, D2, "Half Day", "Present"),
		attendance("amir", A, D1, "Absent"),
		attendance("amir", A, D2, "Half Day", "Absent"),
		attendance("sam", SUB, D1, "Present"),
		attendance("bob", B, D1, "Present"),
		attendance("bob", B, D2, "Present"),
	],
	"Holiday": [],
}


class TestOneAuthorizedPopulation(unittest.TestCase):
	def run_report(self, filters, *, fence, match=None, descendants=()):
		_qb_stub.install(TABLES)
		fenced = types.SimpleNamespace(allowed_companies=lambda user=None: list(fence))
		base = {"filter_based_on": "Date Range", "start_date": "2026-08-01", "end_date": "2026-08-05"}
		with (
			patch.object(report_scope, "is_hr", return_value=True),
			patch.dict(sys.modules, {"hrms.overrides.company_scope": fenced}),
			patch.object(report, "get_descendants_of", lambda doctype, name: list(descendants)),
			patch.object(
				report,
				"date_diff",
				lambda end, start: (date.fromisoformat(end) - date.fromisoformat(start)).days,
			),
			patch.object(report, "build_qb_match_conditions", lambda doctype, user=None: list(match or [])),
			patch.object(report, "get_employee_holiday_map", lambda details, filters: {}),
			patch.object(frappe, "scrub", lambda text: (text or "").lower().replace(" ", "_"), create=True),
			patch.object(report, "getdate", _getdate),
			patch.object(report, "get_date_range", _date_range),
			patch.object(frappe, "msgprint", create=True),
		):
			return report.execute(frappe._dict({**base, **filters}))

	def employees_in(self, data):
		return sorted({row["employee"] for row in data if row.get("employee")})

	def test_a_fenced_hr_user_asking_for_another_company_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.run_report({"company": B}, fence=[A])

	def test_descendants_outside_the_fence_never_reach_rows_or_chart(self):
		_c, data, _m, chart = self.run_report(
			{"company": A, "include_company_descendants": 1}, fence=[A], descendants=[SUB]
		)
		self.assertEqual(self.employees_in(data), ["alice", "amir"])
		# day 1: alice present, amir absent — sam's present day never counted
		self.assertEqual(chart["data"]["datasets"][1]["values"][2], 1, "present on 3 Aug")

	def test_native_employee_restrictions_scope_rows_summary_and_chart_together(self):
		Employee = frappe.qb.DocType("Employee")
		only_sales = [Employee.department == "Sales"]
		_c, data, _m, chart = self.run_report({"company": A}, fence=[], match=only_sales)
		self.assertEqual(self.employees_in(data), ["amir"])
		self.assertEqual(chart["data"]["datasets"][0]["values"][2], 1, "absent on 3 Aug: amir only")
		self.assertEqual(chart["data"]["datasets"][1]["values"][2], 0, "alice's present day is not counted")

	def test_summarized_view_uses_the_same_population(self):
		Employee = frappe.qb.DocType("Employee")
		_c, data, _m, _chart = self.run_report(
			{"company": A, "summarized_view": 1}, fence=[], match=[Employee.department == "Sales"]
		)
		self.assertEqual(self.employees_in(data), ["amir"])


if __name__ == "__main__":
	unittest.main()
