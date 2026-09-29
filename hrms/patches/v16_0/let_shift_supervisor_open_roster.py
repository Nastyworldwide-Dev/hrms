"""Let a Shift Supervisor open the roster (Fahmie, 29 Sep 2026).

He held the right roles (Employee, Shift Supervisor) and still hit two walls:
  · Desk "Shift & Attendance" said "No permission for Page": the workspace was
    gated to HR only by gate_hr_workspaces_to_hr_roles.
  · The roster filter bar (roster/src/components/MonthViewHeader.vue) showed
    six "Insufficient Permission for Branch / Designation" errors: the role
    could not read those two name lists.

Then "report attendance" (owner, same day): the role gets the Monthly
Attendance Sheet, which narrows itself to the supervisor and their direct
reports (hrms.utils.report_scope.report_employees) before reading attendance.

Read only on the lists; what the role can CHANGE stays fenced to the leader's
own team by hrms.api.roster._ensure_can_roster.

A new patch rather than a re-run of add_shift_supervisor_role: that one also
touches Shift Assignment, whose permissions Frappe now refuses to re-validate
(System Manager holds level 1 there with no level 0), so re-running it would
stop the deploy. Idempotent.
"""

import logging

import frappe
from frappe.permissions import add_permission, update_permission_property

logger = logging.getLogger(__name__)

ROLE = "Shift Supervisor"
READ_LISTS = ("Branch", "Designation")
WORKSPACE = "Shift & Attendance"
REPORT = "Monthly Attendance Sheet"


def execute():
	if not frappe.db.exists("Role", ROLE):
		logger.info("[patch] no %s role on this site, nothing to open", ROLE)
		return

	for doctype in READ_LISTS:
		add_permission(doctype, ROLE, 0)
		update_permission_property(doctype, ROLE, 0, "read", 1)

	_open_workspace()
	_open_report()
	frappe.clear_cache()


def _open_workspace():
	"""Let the role open the Shift & Attendance workspace on Desk."""
	if not frappe.db.exists("Workspace", WORKSPACE):
		return
	workspace = frappe.get_doc("Workspace", WORKSPACE)
	if ROLE in {row.role for row in workspace.roles}:
		return
	workspace.append("roles", {"role": ROLE})
	workspace.flags.ignore_permissions = True
	workspace.flags.ignore_links = True
	workspace.save()
	logger.info("[patch] %s can now open the %s workspace", ROLE, WORKSPACE)


def _open_report():
	"""Let the role run the attendance sheet, which fences itself to the team.

	A standard Report refuses save() outside developer mode, so the role row is
	written directly, as restrict_staff_script_reports removes them.
	"""
	if not frappe.db.exists("Report", REPORT):
		return
	if frappe.db.exists("Has Role", {"parenttype": "Report", "parent": REPORT, "role": ROLE}):
		return
	frappe.get_doc(
		{
			"doctype": "Has Role",
			"parenttype": "Report",
			"parentfield": "roles",
			"parent": REPORT,
			"role": ROLE,
		}
	).db_insert()
	frappe.clear_document_cache("Report", REPORT)
	logger.info("[patch] %s can now run %s (own team only)", ROLE, REPORT)
