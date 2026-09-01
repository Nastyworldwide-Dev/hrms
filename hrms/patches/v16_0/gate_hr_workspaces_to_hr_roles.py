"""Hide the HR/Payroll Desk workspaces from ordinary employees.

THE SYMPTOM: a normal employee — a System User carrying only the Employee
role — signs into Desk and the sidebar shows HR Setup, Payroll, Recruitment,
Shift & Attendance, Tax & Benefits, Leaves, Expenses, Performance and Tenure.
Every one of those nine workspaces shipped `public: 1` with an empty `roles`
table, and `Workspace.is_permitted()` treats an empty roles table as
"visible to everyone".

WHAT IT IS, AND IS NOT. It is navigation noise, not a data breach: audited on
a live site, every doctype, report and page behind those cards denies an
employee at the backend (Salary Slip / Payroll Entry / Job Applicant / HR
Settings / the payroll reports all 403; list views return only the employee's
own rows). But an employee should not be shown a wall of HR cards that all
dead-end in Permission errors — it reads as a broken or over-permissioned app.

WHY A PATCH, NOT JUST THE JSON. Workspaces are not re-synced from their JSON on
`bench migrate` (only fresh installs / developer_mode import them), so editing
the source alone never reaches a running site. This sets the roles on the live
records.

Idempotent and non-destructive: only ADDS the three HR roles, and only when
they are missing, so a workspace an operator has already scoped further is left
alone.
"""

import frappe

HR_WORKSPACES = (
	"HR Setup",
	"Payroll",
	"Recruitment",
	"Tax & Benefits",
	"Leaves",
	"Expenses",
	"Shift & Attendance",
	"Performance",
	"Tenure",
)
HR_ROLES = ("HR User", "HR Manager", "System Manager")


def execute():
	for name in HR_WORKSPACES:
		if not frappe.db.exists("Workspace", name):
			continue
		workspace = frappe.get_doc("Workspace", name)
		existing = {row.role for row in workspace.roles}
		missing = [role for role in HR_ROLES if role not in existing]
		if not missing:
			continue
		for role in missing:
			workspace.append("roles", {"role": role})
		workspace.flags.ignore_permissions = True
		workspace.flags.ignore_links = True
		workspace.save()
		frappe.logger("hrms").info("[patch] gated workspace %s to HR roles (added %s)", name, missing)
