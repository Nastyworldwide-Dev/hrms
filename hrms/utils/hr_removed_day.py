"""A day HR removed in the Shift Attendance editor stays removed.

Removing a day cancels its Attendance and leaves nothing HR-owned behind, so
without a durable marker every automation path could mark the day again: the
hourly Absent sweep (a day whose only punches were Rejected looks punchless),
the hourly job reading a punch that arrived later (an import, an approved late
check-out), the ERP-import re-mark, the off-shift heal and attendance recovery
(Group 2-4 review C1, 14 Sep 2026).

The marker is one skip-stamped Employee Checkin with device_id
HR_REMOVED_DEVICE, written on every removal, its `time` on the removed day.
Every automation path asks `removed_by_hr` / `removed_days` and leaves such a
day alone; `attendance_master_edit.hand_back` (and a later HR edit of the day)
deletes the marker, which is the only way the day returns to automation.

Kept dependency-free (frappe only) so the shift type engine, the import, the
heal, the late check-out repair and recovery can all import it without cycles.
"""

import logging
from datetime import datetime, time

import frappe
from frappe.utils import getdate

logger = logging.getLogger(__name__)

#: device_id of the skip-stamped marker punch that keeps a removed day removed
HR_REMOVED_DEVICE = "HR master edit: removed day"
#: in the Comment on every punch the editor skip-stamps; hand_back clears only those
SKIP_MARKER = "[hr-master-edit:skip]"


def removed_days(employee, start_date, end_date) -> set:
	"""Dates in [start_date, end_date] that HR removed for this employee."""
	start, end = getdate(start_date), getdate(end_date)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"device_id": HR_REMOVED_DEVICE,
			"time": ("between", [datetime.combine(start, time.min), datetime.combine(end, time.max)]),
		},
		pluck="time",
	)
	days = {getdate(moment) for moment in rows}
	if days:
		logger.info("[hr_removed_day] %s: %d HR-removed day(s) in %s..%s", employee, len(days), start, end)
	return days


def removed_by_hr(employee, day) -> bool:
	"""Whether HR removed this employee's day in the Shift Attendance editor."""
	return bool(employee and day and removed_days(employee, day, day))


def hold_punches(names, day) -> None:
	"""Skip-stamp punches that reached a removed day, with the editor's marker
	comment, so hand_back releases them together with the rest of the day."""
	for name in names:
		frappe.db.set_value("Employee Checkin", name, "skip_auto_attendance", 1)
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Employee Checkin",
				"reference_name": name,
				"content": f"{SKIP_MARKER} Day {day} was removed by HR in Shift Attendance; "
				"this punch is kept but not marked. Hand the day back to use it.",
			}
		).insert(ignore_permissions=True)
	logger.info("[hr_removed_day] %d punch(es) on HR-removed %s held: %s", len(names), day, list(names))
