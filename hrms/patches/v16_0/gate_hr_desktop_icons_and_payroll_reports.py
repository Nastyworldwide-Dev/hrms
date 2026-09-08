"""Give the nine HR launcher tiles and two payroll reports their HR roles on live sites.

THE SYMPTOM (7 Sep 2026 audit, D1 + D2): an ordinary employee's Desk launcher
showed every child of the Nadi icon — Payroll included — and the Professional
Tax / Provident Fund deduction reports were open to any Desk user.

WHY. The 1 Sep patch role-gated the workspace PAGES, but v16 filters
"Workspace Sidebar" desktop icons by the icon's own roles table
(frappe/desk/doctype/desktop_icon/desktop_icon.py), which shipped empty — and
an empty roles table means everyone. The two reports carry HR roles in their
JSON, but their `modified` still read 2022, so the timestamp-gated import
never delivered those roles to a site that already had the report; zero
`Has Role` rows on a report means visible to all.

The shipped JSONs are corrected alongside this patch (roles plus a fresh
`modified`) for new sites. This patch reaches the rows already on a site.
Idempotent and non-destructive: it only ADDS the three HR roles, and only
when missing, so a row an operator already scoped further is left alone —
the same shape as gate_hr_workspaces_to_hr_roles.
"""

import logging

import frappe

# One source for the operator set; hrms/tests/test_is_hr_single_source.py pins it.
from hrms.hr.utils import HR_ROLES

logger = logging.getLogger(__name__)

HR_ICONS = (
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
PAYROLL_REPORTS = ("Professional Tax Deductions", "Provident Fund Deductions")


def _ensure_roles(doctype, name):
	if not frappe.db.exists(doctype, name):
		logger.info("[gate_hr_desktop_icons] %s %s absent on this site — skipped", doctype, name)
		return
	doc = frappe.get_doc(doctype, name)
	existing = {row.role for row in doc.roles}
	missing = [role for role in sorted(HR_ROLES) if role not in existing]
	if not missing:
		return
	for role in missing:
		doc.append("roles", {"role": role})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.save()
	logger.info("[gate_hr_desktop_icons] %s %s: added %s", doctype, name, missing)


def execute():
	for name in HR_ICONS:
		_ensure_roles("Desktop Icon", name)
	for name in PAYROLL_REPORTS:
		_ensure_roles("Report", name)
