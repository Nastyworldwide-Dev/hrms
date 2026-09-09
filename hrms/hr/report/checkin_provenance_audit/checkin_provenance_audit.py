"""Checkin Provenance Audit — script report.

Who really made each punch, and what the sync did to it. One row per Employee
Checkin in the window: local (made here, untouched), mirrored (pulled from the
source), or OVERWRITTEN — a punch made here that a pull replaced under a
colliding name (hrms/sync/checkin_recovery.py tells the story). For an
overwritten row the report shows the true employee and time recovered from
owner and creation, the log type and where it came from, what the recovery
would do, and the true employee's attendance for that day, so HR can see the
Absent / Half Day the lost punch caused before anything is written back.

Filters: from_date, to_date (default: first day of last month → today),
employee, kind (Overwritten by default; All shows everything).
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import add_months, get_first_day, getdate

from hrms.sync import checkin_recovery

logger = logging.getLogger(__name__)

KINDS = {
	"Overwritten": checkin_recovery.OVERWRITTEN,
	"Mirrored": checkin_recovery.MIRRORED,
	"Local": checkin_recovery.LOCAL,
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_defaults(filters)
	logger.info("[checkin_provenance_audit] execute filters=%s", dict(filters))
	collected = checkin_recovery.collect(filters.from_date, filters.to_date, filters.get("employee"))
	rows = _rows(collected)
	message = _summary(collected)
	wanted = KINDS.get(filters.get("kind"))
	if wanted:
		rows = [r for r in rows if r["kind"] == wanted]
	rows.sort(
		key=lambda r: (
			r.get("true_employee") or r.get("employee") or "",
			str(r.get("true_time") or r.get("time")),
		)
	)
	return _columns(), rows, message


def _apply_defaults(filters):
	if not filters.get("to_date"):
		filters["to_date"] = frappe.utils.today()
	if not filters.get("from_date"):
		filters["from_date"] = get_first_day(add_months(getdate(filters["to_date"]), -1))
	if not filters.get("kind"):
		filters["kind"] = "Overwritten"


def _rows(collected: dict) -> list:
	plan_by_name = {e["source_name"]: e for e in collected["plan"]}
	attendance = collected["attendance"]
	rows = []
	for punch in collected["rows"]:
		entry = plan_by_name.get(punch["name"])
		row = {
			**{
				k: punch.get(k)
				for k in (
					"name",
					"kind",
					"reason",
					"synced_from_instance",
					"employee",
					"time",
					"log_type",
					"owner",
					"creation",
				)
			},
			"true_employee": entry["employee"]
			if entry
			else (punch.get("employee") if punch["kind"] == checkin_recovery.LOCAL else None),
			"true_time": entry["time"] if entry else None,
			"true_log_type": entry["log_type"] if entry else None,
			"confidence": entry["confidence"] if entry else None,
			"planned_action": entry["action"] if entry else "",
		}
		day = attendance.get((row["true_employee"], getdate(row["true_time"]))) if entry else None
		row.update(
			{
				"attendance": day.name if day else None,
				"attendance_status": day.status if day else "",
				"working_hours": day.working_hours if day else None,
				"attendance_source": _attendance_source(day),
			}
		)
		rows.append(row)
	return rows


def _attendance_source(day) -> str:
	if not day:
		return ""
	if day.get("synced_from_instance"):
		return "mirrored"
	return "job" if day.get("auto_attendance") else "manual"


def _summary(collected: dict) -> str:
	counts = {kind: 0 for kind in KINDS.values()}
	for punch in collected["rows"]:
		counts[punch["kind"]] = counts.get(punch["kind"], 0) + 1
	inserts = sum(1 for e in collected["plan"] if e["action"] == "insert")
	skips = len(collected["plan"]) - inserts
	return _("Overwritten {0} · Mirrored {1} · Local {2} · Plan: insert {3}, skip {4}").format(
		counts[checkin_recovery.OVERWRITTEN],
		counts[checkin_recovery.MIRRORED],
		counts[checkin_recovery.LOCAL],
		inserts,
		skips,
	)


def _columns():
	def col(fieldname, label, fieldtype="Data", width=120, options=None):
		column = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
		if options:
			column["options"] = options
		return column

	return [
		col("name", "Check-in", "Link", 200, "Employee Checkin"),
		col("kind", "Kind", width=100),
		col("reason", "Why", width=200),
		col("synced_from_instance", "Stamped From", width=110),
		col("employee", "Shown Employee", "Link", 150, "Employee"),
		col("time", "Shown Time", "Datetime", 150),
		col("log_type", "Shown Type", width=80),
		col("owner", "Created By", width=180),
		col("creation", "Created On", "Datetime", 150),
		col("true_employee", "True Employee", "Link", 150, "Employee"),
		col("true_time", "True Time", "Datetime", 150),
		col("true_log_type", "True Type", width=80),
		col("confidence", "Type Source", width=90),
		col("planned_action", "Recovery", width=140),
		col("attendance", "Attendance", "Link", 170, "Attendance"),
		col("attendance_status", "Status", width=90),
		col("working_hours", "Hours", "Float", 70),
		col("attendance_source", "Att. Source", width=110),
	]
