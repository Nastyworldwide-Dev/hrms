"""Create the "Attendance Report Viewer" role (owner, 14 Oct 2026).

Shenzhen staff count their team's attendance every month and had to ask HR
for the Shift Attendance report each time. Holding this role lets that report
show everyone in the holder's Company User Permissions
(hrms.utils.report_scope.attendance_viewer_companies). The report already
lists Employee among its roles, so no Has Role row is needed; desk_access is
on so the holder can open the report in Desk. Grants no doctype permission.
Idempotent.
"""

import logging

import frappe

from hrms.utils.report_scope import ATTENDANCE_VIEWER_ROLE

logger = logging.getLogger(__name__)

def execute():
	if frappe.db.exists("Role", ATTENDANCE_VIEWER_ROLE):
		return
	role = frappe.new_doc("Role")
	role.role_name = ATTENDANCE_VIEWER_ROLE
	role.desk_access = 1
	role.insert(ignore_permissions=True)
	logger.info("[patch] created role %s", ATTENDANCE_VIEWER_ROLE)
