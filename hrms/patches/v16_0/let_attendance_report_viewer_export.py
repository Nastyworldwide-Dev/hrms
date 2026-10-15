"""Let an Attendance Report Viewer download Shift Attendance (owner, 15 Oct 2026).

The Shenzhen staff count the month in Excel. A Script Report exports only for
a role holding `export` on its ref doctype (frappe.permissions.can_export on
Attendance), which no staff role has. Read, report and export on Attendance
are given to this role alone. Which rows a list or an export of Attendance
holds is still the row scope's (employee_owned_row_scope: their own), and the
Shift Attendance report keeps its company fence
(report_scope.attendance_viewer_companies). No write, create or submit.
Idempotent.
"""

import logging

import frappe
from frappe.permissions import add_permission, update_permission_property

from hrms.utils.report_scope import ATTENDANCE_VIEWER_ROLE

logger = logging.getLogger(__name__)


def execute():
	if not frappe.db.exists("Role", ATTENDANCE_VIEWER_ROLE):
		logger.info("[patch] no %s role on this site, nothing to open", ATTENDANCE_VIEWER_ROLE)
		return
	add_permission("Attendance", ATTENDANCE_VIEWER_ROLE, 0)
	for ptype in ("read", "report", "export"):
		update_permission_property("Attendance", ATTENDANCE_VIEWER_ROLE, 0, ptype, 1)
	frappe.clear_cache(doctype="Attendance")
	logger.info("[patch] %s can now export Shift Attendance", ATTENDANCE_VIEWER_ROLE)
