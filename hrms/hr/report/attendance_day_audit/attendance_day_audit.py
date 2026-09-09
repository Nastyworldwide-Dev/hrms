"""Attendance Day Audit — script report.

One row per employee-day: the punches, the attendance row, and the VERDICT —
why the day reads the way it does, in the words of the mechanism
(hrms/utils/attendance_day_audit.py judge_day) — plus what the repair would do.
Built for 7 September 2026, when staff had punched and the calendar said
Absent, Half Day or nothing, each for a different reason.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from hrms.utils import attendance_day_audit

logger = logging.getLogger(__name__)

VERDICT_LABELS = {
	"marked": "Marked from its punches",
	"half-day-one-punch": "Half Day from one punch",
	"unread-punches": "Unread punches — waiting for the hourly job",
	"punches-skip-stamped": "Punches skip-stamped (old failure)",
	"punches-linked-to-cancelled-row": "Punches linked to a cancelled row",
	"punches-mirrored": "Punches are mirrored rows",
	"punches-rejected": "Punches rejected",
	"punch-without-shift": "Punch resolved to no shift",
	"shift-mismatch": "Punch shift ≠ attendance shift",
	"shift-auto-attendance-off": "Shift has auto attendance off",
	"before-process-attendance-after": "Before Process Attendance After",
	"after-last-sync": "Job has not reached this shift yet",
	"row-financially-locked": "Payroll / claim depends on this day — HR corrects by hand",
	"row-manual": "Manual attendance row",
	"row-mirrored": "Mirrored attendance row",
	"row-leave": "Leave record",
	"no-punches": "No punches",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("to_date"):
		filters["to_date"] = frappe.utils.today()
	if not filters.get("from_date"):
		filters["from_date"] = add_days(getdate(filters["to_date"]), -14)
	logger.info("[attendance_day_audit] execute filters=%s", dict(filters))
	days = attendance_day_audit.collect(filters.from_date, filters.to_date, filters.get("employee"))["days"]
	wanted = filters.get("verdict")
	if wanted and wanted != "All":
		days = [d for d in days if d["verdict"] == wanted]
	rows = [{**d, "verdict_label": _(VERDICT_LABELS.get(d["verdict"], d["verdict"]))} for d in days]
	repairs = sum(1 for d in days if d.get("repair"))
	message = _("{0} employee-days · {1} repairable by clearing old skip stamps / dead links").format(
		len(days), repairs
	)
	return _columns(), rows, message


def _columns():
	def col(fieldname, label, fieldtype="Data", width=120, options=None):
		column = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
		if options:
			column["options"] = options
		return column

	return [
		col("employee", "Employee", "Link", 130, "Employee"),
		col("employee_name", "Name", width=160),
		col("date", "Date", "Date", 100),
		col("punches", "Punches", width=220),
		col("attendance", "Attendance", "Link", 170, "Attendance"),
		col("status", "Status", width=90),
		col("working_hours", "Hours", "Float", 70),
		col("shift", "Shift", "Link", 130, "Shift Type"),
		col("verdict_label", "Verdict", width=260),
		col("detail", "Detail", width=420),
		col("repair", "Repair", width=80),
	]
