"""The Salary Register never returns another company's slips to a fenced HR user.

360 audit (Desk reports): the report applied the caller's company FILTER but
no company FENCE. A Script Report runs its own SQL — Frappe checks the
report's roles and stops — so an HR (Company) user who left the company
filter blank, or typed another company's name, was handed every company's
salary slips and component totals. The app's own company scope (a Company
User Permission, ignoring applicable_for, the same rule the PWA endpoints
use) is now applied before slips are selected and before components are
aggregated, and a request for a company outside the fence is refused.

Bench-free: the query builder runs against in-memory rows (_qb_stub), the
fence collaborator is stubbed, everything else is the real report.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_salary_register.py
"""

import sys
import types
import unittest
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

from hrms.payroll.report.salary_register import salary_register as report
from hrms.utils import report_scope

A, B = "Company A", "Company B"


def slip(name, company, employee, basic, docstatus=1):
	return dict(
		name=name,
		company=company,
		employee=employee,
		employee_name=employee.title(),
		docstatus=docstatus,
		start_date="2026-08-01",
		end_date="2026-08-31",
		currency="MYR",
		exchange_rate=1,
		branch=None,
		department=None,
		designation=None,
		leave_without_pay=0,
		absent_days=0,
		payment_days=31,
		total_loan_repayment=0,
		gross_pay=basic,
		total_deduction=0,
		net_pay=basic,
		rounded_total=basic,
		_basic=basic,
	)


TABLES = {
	"Salary Slip": [
		slip("SS-A1", A, "alice", 3000),
		slip("SS-A2", A, "amir", 3500),
		slip("SS-B1", B, "bob", 9000),
	],
	"Salary Detail": [
		dict(parent="SS-A1", parentfield="earnings", salary_component="Basic", amount=3000),
		dict(parent="SS-A2", parentfield="earnings", salary_component="Basic", amount=3500),
		dict(parent="SS-B1", parentfield="earnings", salary_component="Basic", amount=9000),
	],
	"Salary Component": [dict(name="Basic", type="Earning")],
	"Employee": [
		dict(name="alice", date_of_joining="2020-01-01"),
		dict(name="bob", date_of_joining="2019-01-01"),
	],
}


class TestSalaryRegisterFence(unittest.TestCase):
	def run_report(self, filters, *, fence):
		_qb_stub.install(TABLES)
		fenced = types.SimpleNamespace(allowed_companies=lambda user=None: list(fence))
		with (
			patch.object(report_scope, "is_hr", return_value=True),
			patch.dict(sys.modules, {"hrms.overrides.company_scope": fenced}),
			patch.object(frappe, "scrub", lambda text: text.lower().replace(" ", "_"), create=True),
			patch.object(
				frappe.db, "get_value", side_effect=lambda doctype, name, field=None, **kw: "Earning"
			),
		):
			return report.execute(frappe._dict(filters))

	def test_a_fenced_hr_user_with_no_company_filter_sees_only_their_companies(self):
		_columns, data = self.run_report({"docstatus": "Submitted"}, fence=[A])
		self.assertEqual(sorted(row["salary_slip_id"] for row in data), ["SS-A1", "SS-A2"])
		self.assertNotIn(
			9000, [row.get("basic") for row in data], "the other company's component total leaked"
		)

	def test_a_fenced_hr_user_asking_for_another_company_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self.run_report({"docstatus": "Submitted", "company": B}, fence=[A])

	def test_a_fenced_hr_user_asking_for_their_own_company_gets_it(self):
		_columns, data = self.run_report({"docstatus": "Submitted", "company": A}, fence=[A])
		self.assertEqual(sorted(row["salary_slip_id"] for row in data), ["SS-A1", "SS-A2"])

	def test_an_unfenced_hr_user_keeps_the_whole_register_and_their_chosen_company(self):
		_columns, data = self.run_report({"docstatus": "Submitted"}, fence=[])
		self.assertEqual(len(data), 3)
		_columns, data = self.run_report({"docstatus": "Submitted", "company": B}, fence=[])
		self.assertEqual([row["salary_slip_id"] for row in data], ["SS-B1"])

	def test_the_other_filters_still_apply_inside_the_fence(self):
		_columns, data = self.run_report({"docstatus": "Draft"}, fence=[A])
		self.assertEqual(data, [])
		_columns, data = self.run_report({"docstatus": "Submitted", "employee": "amir"}, fence=[A])
		self.assertEqual([row["salary_slip_id"] for row in data], ["SS-A2"])


if __name__ == "__main__":
	unittest.main()
