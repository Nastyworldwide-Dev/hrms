"""Fill the hours of half-day leave days left at 0.00 (owner, 11 Nov 2026).

Live: Irfan, 10 Nov: a half-day leave approved the day before created the row
(Half Day, no times, 0 h); the hourly job closed its wait during his morning
shift; his 09:01 IN and 13:33 OUT were then linked to the row as evidence and
the hours stayed 0.00. Every half day approved ahead of its date was exposed.
The cause is fixed in ShiftType.mark_absent_for_half_day_dates and
get_existing_half_day_attendance; this repairs the rows it already left behind.

A row is repaired when it is a submitted Half Day with a leave behind it, no
in or out time, 0 hours, a shift, and the punches linked to it pair into a
day under that shift's own rules (ShiftType.get_attendance). Only the in and
out times, the hours and the late/early marks are written; the status, the
leave and who owns the row are not touched. A row whose punches do not pair
(one punch only) is left as it is and logged for HR. Idempotent: a repaired
row has times and is never read again.
"""

import logging

import frappe
from frappe.utils import flt

logger = logging.getLogger(__name__)


def stuck_rows():
	return frappe.get_all(
		"Attendance",
		filters={
			"docstatus": 1,
			"status": "Half Day",
			"leave_application": ("is", "set"),
			"in_time": ("is", "not set"),
			"out_time": ("is", "not set"),
			"working_hours": ("in", [0, None]),
			"shift": ("is", "set"),
		},
		fields=["name", "employee", "attendance_date", "shift"],
		order_by="attendance_date asc",
	)


def repair_values(day) -> dict | None:
	"""The values to write from a marking result, or None when the punches gave
	no pair. Pure: `day` is ShiftType.get_attendance's tuple or None."""
	if not day:
		return None
	_status, hours, late, early, in_time, out_time = day
	if not (in_time and out_time) or flt(hours) <= 0:
		return None
	return {
		"in_time": in_time,
		"out_time": out_time,
		"working_hours": flt(hours),
		"late_entry": int(bool(late)),
		"early_exit": int(bool(early)),
		"half_day_status": "Present",
		"modify_half_day_status": 0,
	}


def execute():
	from hrms.hr.doctype.shift_type.shift_type import counts_for_attendance, linked_checkins

	rows = stuck_rows()
	repaired, unpaired = 0, []
	for row in rows:
		logs = [log for log in linked_checkins(row.name) if counts_for_attendance(log)]
		shift = frappe.get_cached_doc("Shift Type", row.shift)
		values = repair_values(
			shift.get_attendance(
				logs,
				flt(shift.working_hours_threshold_for_absent),
				flt(shift.working_hours_threshold_for_half_day),
			)
			if len(logs) >= 2
			else None
		)
		if not values:
			unpaired.append(row.name)
			continue
		frappe.db.set_value("Attendance", row.name, values, update_modified=False)
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Attendance",
				"reference_name": row.name,
				"content": frappe._(
					"Hours filled from this day's check-in and check-out: in {0}, out {1}, {2} h."
				).format(values["in_time"], values["out_time"], values["working_hours"]),
			}
		).insert(ignore_permissions=True)
		repaired += 1
	logger.info(
		"[patch] half-day leave hours: %d of %d row(s) filled; %d left for HR (punches do not pair): %s",
		repaired,
		len(rows),
		len(unpaired),
		", ".join(unpaired[:50]),
	)
