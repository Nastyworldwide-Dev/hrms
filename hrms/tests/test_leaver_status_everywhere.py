"""Resigned works wherever Left worked (HR, 10 Nov 2026).

Payslip and leave-accrual rules lifted by AST, so the suite runs without a
bench (both modules import erpnext at load time):

    python3 -m pytest hrms/tests/test_leaver_status_everywhere.py
"""

import ast
import datetime
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from hrms.utils.employee_status import LEAVER_STATUS, is_leaver

HRMS = pathlib.Path(__file__).resolve().parents[1]
SALARY_SLIP = HRMS / "payroll" / "doctype" / "salary_slip" / "salary_slip.py"
HR_UTILS = HRMS / "hr" / "utils.py"


class _Refused(Exception):
	pass


def _lift_method(source, cls, name, namespace):
	tree = ast.parse(source.read_text())
	body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls).body
	fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), namespace)
	return namespace[name]


def _getdate(v=None):
	return v if isinstance(v, datetime.date) else datetime.date.fromisoformat(v)


class TestFinalPayslip(unittest.TestCase):
	"""A payslip for someone relieved before the period must find them gone."""

	def payslip(self, status):
		frappe = MagicMock()
		frappe.throw.side_effect = _Refused
		frappe.db.get_value.return_value = status
		ns = {
			"frappe": frappe,
			"_": lambda s: s,
			"getdate": _getdate,
			"is_leaver": is_leaver,
			"LEAVER_STATUS": LEAVER_STATUS,
			"get_link_to_form": lambda *a: "E1",
			"formatdate": str,
			"date_diff": lambda a, b: (a - b).days,
			"cint": lambda v: int(v or 0),
		}
		get_payment_days = _lift_method(SALARY_SLIP, "SalarySlip", "get_payment_days", ns)
		slip = SimpleNamespace(
			employee="E1",
			joining_date=datetime.date(2020, 1, 1),
			relieving_date=datetime.date(2026, 9, 30),
			start_date="2026-10-01",
			end_date="2026-10-31",
			actual_start_date=datetime.date(2026, 10, 1),
			actual_end_date=datetime.date(2026, 10, 31),
		)
		return get_payment_days(slip, include_holidays_in_total_working_days=1)

	def test_a_resigned_employee_is_paid_out(self):
		self.assertEqual(self.payslip("Resigned"), 31)

	def test_anyone_else_relieved_earlier_is_asked_to_be_set_resigned(self):
		for status in ("Active", "Terminated", "Deceased", "Suspended"):
			with self.assertRaises(_Refused, msg=status):
				self.payslip(status)


class TestLeaveAccrual(unittest.TestCase):
	def test_earned_leave_stops_for_resigned_not_left(self):
		source = HR_UTILS.read_text()
		self.assertIn("(employee.status != LEAVER_STATUS)", source)
		self.assertNotIn('(employee.status != "Left")', source)


if __name__ == "__main__":
	unittest.main()
