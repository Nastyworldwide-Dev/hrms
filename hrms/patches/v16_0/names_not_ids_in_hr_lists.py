"""Drop the employee ID column from saved HR request list columns.

HR, 15 Sep 2026: show the employee's name, not the ID, "for easier work for hr".
The doctypes now title their lists with the employee name and no longer list the
ID. But once anyone uses the column picker, `List View Settings.fields` replaces
the doctype's columns site-wide, so on a site where HR arranged these lists the
ID column would stay. This removes only the ID and the repeated name columns and
keeps every other column HR chose.
"""

import json
import logging

import frappe

logger = logging.getLogger(__name__)

#: doctype -> columns the name title makes redundant
REDUNDANT_COLUMNS = {
	"OT Request": {"employee", "employee_name"},
	"Replacement Leave Claim": {"employee", "employee_name"},
	"Employee Issue": {"employee", "employee_name"},
	"Remote Checkin Request": {"employee", "employee_name"},
	"Attendance Request": {"employee", "employee_name"},
	"Shift Request": {"employee", "employee_name"},
	"Shift Schedule Assignment": {"employee", "employee_name"},
	"Compensatory Leave Request": {"employee", "employee_name"},
	"Employee Advance": {"employee", "employee_name"},
	"Overtime Slip": {"employee", "employee_name"},
	"Shift Swap Request": {"requesting_employee", "requesting_employee_name", "target_employee"},
}


def drop_id_columns(saved: str | None, fieldnames: set) -> str | None:
	"""The saved column set without `fieldnames`, or None to leave it alone.

	None: nothing saved, unreadable (left for a human), or nothing to drop.
	"" when every saved column was redundant: the doctype default applies.
	"""
	if not saved or not saved.strip():
		return None
	try:
		columns = json.loads(saved)
	except (ValueError, TypeError):
		return None
	if not isinstance(columns, list) or not all(isinstance(column, dict) for column in columns):
		return None
	kept = [column for column in columns if column.get("fieldname") not in fieldnames]
	if len(kept) == len(columns):
		return None
	return json.dumps(kept) if kept else ""


def execute():
	touched = []
	for doctype, fieldnames in REDUNDANT_COLUMNS.items():
		if not frappe.db.exists("List View Settings", doctype):
			continue
		saved = frappe.db.get_value("List View Settings", doctype, "fields")
		updated = drop_id_columns(saved, fieldnames)
		if updated is None:
			continue
		frappe.db.set_value("List View Settings", doctype, "fields", updated)
		touched.append(doctype)
	logger.info(
		"[names_not_ids_in_hr_lists] dropped ID columns from saved list columns of %s", touched or "none"
	)
