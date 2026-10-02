"""Let a Shift Supervisor read their team's Attendance and clock-ins on Desk (owner, 2 Oct 2026).

Read and report only — no write, create, submit or export. Which rows they see
is fenced to the people they roster by
hrms.overrides.employee_owned_row_scope.SUPERVISOR_READ_DOCTYPES; this patch
only lets the role open the two lists at all. Employee Checkin's time fields
sit at permlevel 1, so that level gets read too. Idempotent.

The Shift & Attendance sidebar has no "Attendance" link (HR reaches it from
the workspace page); one is added beside "Employee Checkin" so a supervisor
finds it. Frappe shows a sidebar link only to users who can read it.

Not add_shift_supervisor_role: re-running it fails on Shift Assignment's
permissions (see let_shift_supervisor_open_roster).
"""

import logging

import frappe
from frappe.permissions import add_permission, update_permission_property

from hrms.patches.v16_0.add_forgotten_checkouts_link import _insert, _save

logger = logging.getLogger(__name__)

ROLE = "Shift Supervisor"
#: doctype -> permlevels to open for reading
READS = {"Attendance": (0,), "Employee Checkin": (0, 1)}
SIDEBAR = "Shift & Attendance"


def execute():
	if not frappe.db.exists("Role", ROLE):
		logger.info("[patch] no %s role on this site, nothing to open", ROLE)
		return
	for doctype, levels in READS.items():
		for level in levels:
			add_permission(doctype, ROLE, level)
			update_permission_property(doctype, ROLE, level, "read", 1)
			if level == 0:
				update_permission_property(doctype, ROLE, level, "report", 1)
		logger.info("[patch] %s can now read %s (own team only)", ROLE, doctype)
	_link_attendance_in_sidebar()
	frappe.clear_cache()


def _link_attendance_in_sidebar():
	if not frappe.db.exists("Workspace Sidebar", SIDEBAR):
		return
	doc = frappe.get_doc("Workspace Sidebar", SIDEBAR)
	# "Dashboard" links to the Attendance DASHBOARD; only a DocType link counts
	if any(i.type == "Link" and i.link_type == "DocType" and i.link_to == "Attendance" for i in doc.items):
		return
	anchor = next((n for n, item in enumerate(doc.items) if item.link_to == "Employee Checkin"), None)
	if anchor is None:
		logger.info("[patch] %s sidebar has no Employee Checkin — Attendance not linked", SIDEBAR)
		return
	_insert(
		doc,
		"items",
		anchor,
		{
			"child": 0,
			"collapsible": 1,
			"icon": "calendar-days",
			"indent": 0,
			"keep_closed": 0,
			"label": "Attendance",
			"link_to": "Attendance",
			"link_type": "DocType",
			"show_arrow": 0,
			"type": "Link",
		},
	)
	_save(doc, "Workspace Sidebar")
