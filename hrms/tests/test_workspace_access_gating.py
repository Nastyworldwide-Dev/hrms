"""Guards that the HR/Payroll Desk workspaces (and the payroll deduction
reports) are role-gated, so an ordinary employee's Desk sidebar does not show a
wall of HR cards that all dead-end in Permission errors.

Frappe's Workspace.is_permitted() treats an EMPTY roles table as visible to
everyone, so an HR workspace with no roles leaks into every desk user's
sidebar. This pins the roles on the JSON (fresh installs) and the patch that
applies them to existing sites. Bench-free.

    python3 hrms/tests/test_workspace_access_gating.py
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

HR_WORKSPACES = {
	"hr/workspace/hr_setup/hr_setup.json",
	"payroll/workspace/payroll/payroll.json",
	"hr/workspace/recruitment/recruitment.json",
	"payroll/workspace/tax_&_benefits/tax_&_benefits.json",
	"hr/workspace/leaves/leaves.json",
	"hr/workspace/expenses/expenses.json",
	"hr/workspace/shift_&_attendance/shift_&_attendance.json",
	"hr/workspace/performance/performance.json",
	"hr/workspace/tenure/tenure.json",
}
GATED_REPORTS = {
	"payroll/report/provident_fund_deductions/provident_fund_deductions.json",
	"payroll/report/professional_tax_deductions/professional_tax_deductions.json",
}
EXPECTED_ROLES = {"HR User", "HR Manager", "System Manager"}
FORBIDDEN_ROLES = {"Employee", "Employee Self Service"}


class TestWorkspaceAccessGating(unittest.TestCase):
	def test_hr_workspaces_are_role_gated_to_hr(self):
		for rel in HR_WORKSPACES:
			meta = json.loads((HRMS_ROOT / rel).read_text())
			roles = {row["role"] for row in meta.get("roles", [])}
			self.assertTrue(
				EXPECTED_ROLES.issubset(roles),
				f"{rel} must be gated to HR roles (has {roles or 'nothing — visible to all'})",
			)
			self.assertFalse(
				roles & FORBIDDEN_ROLES,
				f"{rel} must not grant employee roles the HR workspace",
			)

	def test_payroll_deduction_reports_are_role_gated(self):
		for rel in GATED_REPORTS:
			meta = json.loads((HRMS_ROOT / rel).read_text())
			roles = {row["role"] for row in meta.get("roles", [])}
			self.assertTrue(roles, f"{rel} must not have an empty roles list (open to all desk users)")
			self.assertFalse(roles & FORBIDDEN_ROLES, f"{rel} must not be readable by employee roles")

	def test_patch_is_registered(self):
		patches = (HRMS_ROOT / "patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.gate_hr_workspaces_to_hr_roles", patches)


if __name__ == "__main__":
	unittest.main(verbosity=2)
