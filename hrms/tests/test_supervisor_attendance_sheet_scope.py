"""A Shift Supervisor reads the Monthly Attendance Sheet for their own team only.

Owner, 29 Sep 2026: a supervisor must "report attendance" for the people who
report to them (ruling "A": direct reports, not the whole branch). A Script
Report gets no row scope from Frappe, so the report must narrow its people
before it reads any attendance, or opening it to the role would show every
employee.

Through report_scope.report_employees, with its collaborators stubbed. Bench-free:

    python3 hrms/tests/test_supervisor_attendance_sheet_scope.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = HRMS_ROOT / "utils" / "report_scope.py"
REPORT = HRMS_ROOT / "hr" / "report" / "monthly_attendance_sheet" / "monthly_attendance_sheet.py"
STUBBED = ("frappe", "hrms.hr.utils", "hrms.utils.identity", "hrms.overrides.company_scope")

LEAD, REPORT_EMP = "EMP-LEAD", "EMP-REPORT"


def load(cleanup, *, is_hr, roles, own, reports):
	frappe = types.ModuleType("frappe")
	frappe._dict = dict
	frappe.session = types.SimpleNamespace(user="lead@example.com")
	frappe.get_roles = lambda user=None: list(roles)

	hr_utils = types.ModuleType("hrms.hr.utils")
	hr_utils.sees_all_employee_data = lambda user=None: is_hr
	hr_utils.get_direct_report_employees = lambda user: list(reports)

	identity = types.ModuleType("hrms.utils.identity")
	identity.get_employee = lambda user=None: own

	company_scope = types.ModuleType("hrms.overrides.company_scope")
	company_scope.allowed_companies = lambda user=None: []

	previous = {name: sys.modules.get(name) for name in STUBBED}
	sys.modules.update(
		{
			"frappe": frappe,
			"hrms.hr.utils": hr_utils,
			"hrms.utils.identity": identity,
			"hrms.overrides.company_scope": company_scope,
		}
	)

	def restore():
		for name, saved in previous.items():
			if saved is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = saved

	cleanup(restore)
	spec = importlib.util.spec_from_file_location("report_scope_supervisor", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class TestSupervisorAttendanceSheetScope(unittest.TestCase):
	def test_supervisor_sees_self_and_direct_reports(self):
		scope = load(
			self.addCleanup,
			is_hr=False,
			roles=["Employee", "Shift Supervisor"],
			own=LEAD,
			reports=[REPORT_EMP],
		)
		self.assertEqual(sorted(scope.report_employees()), sorted([LEAD, REPORT_EMP]))

	def test_hr_is_not_narrowed(self):
		scope = load(self.addCleanup, is_hr=True, roles=["HR User"], own=None, reports=[])
		self.assertIsNone(scope.report_employees())

	def test_a_manager_without_the_role_sees_nobody(self):
		scope = load(self.addCleanup, is_hr=False, roles=["Employee"], own=LEAD, reports=[REPORT_EMP])
		self.assertEqual(scope.report_employees(), [])

	def test_supervisor_with_no_employee_record_sees_nobody(self):
		scope = load(self.addCleanup, is_hr=False, roles=["Shift Supervisor"], own=None, reports=[])
		self.assertEqual(scope.report_employees(), [])

	def test_the_sheet_narrows_its_people_before_reading_attendance(self):
		source = REPORT.read_text()
		body = source[source.index("def get_employee_related_details") :]
		body = body[: body.index("\ndef ", 1)]
		self.assertIn("report_employees(", body)
		self.assertLess(
			source.index("get_employee_related_details(filters)"),
			source.index("get_attendance_map(filters)"),
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)
