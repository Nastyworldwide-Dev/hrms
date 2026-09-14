"""Unclaimable Days — script report (S1 of the end-it plan, 15 Sep 2026).

One row per employee-day (or tap / assignment pair) that the read-only
detectors in hrms/utils/attendance_recovery.py (`unclaimable_rows`) found:
family F1..F13, the reason, and a status — fixable (a recovery step fixes it),
on purpose (a leave, HR-kept, HR-removed or paid day: left alone), needs HR
(only HR can fix it in Shift Attendance). Nothing here writes.

HR roles only (HR User included), fenced to the caller's companies the way
Shift Attendance is (`report_scope.scoped_companies`). The planners refuse
nothing by role themselves, so the report never goes through
`inputs_report`'s narrower operator gate.

Filters: from_date / to_date (default 1 Aug → yesterday; today is never
read), employee, family, status. Windows longer than recovery's
MAX_WINDOW_DAYS are read in pieces.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms.utils import attendance_recovery as rec
from hrms.utils.report_scope import scoped_companies

logger = logging.getLogger(__name__)

FAMILIES = [family for family, *_rest in rec.UNCLAIMABLE_FAMILIES]
STATUSES = (rec.STATUS_FIXABLE, rec.STATUS_ON_PURPOSE, rec.STATUS_NEEDS_HR)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_defaults(filters)
	logger.info("[unclaimable_days] execute filters=%s", dict(filters))
	rows = _rows(filters)
	return _columns(), rows, _summary(rows)


def _apply_defaults(filters) -> None:
	today = getdate(now_datetime())
	if not filters.get("from_date"):
		filters["from_date"] = str(rec.REPAIR_FLOOR)
	if not filters.get("to_date"):
		filters["to_date"] = str(today - timedelta(days=1))


def windows(from_date, to_date, today) -> list:
	"""Recovery windows of at most MAX_WINDOW_DAYS covering [from, to], never before
	the repair floor, never past yesterday. Pure."""
	start = max(getdate(from_date), rec.REPAIR_FLOOR)
	end = min(getdate(to_date), today - timedelta(days=1))
	out = []
	while start <= end:
		stop = min(end, start + timedelta(days=rec.MAX_WINDOW_DAYS - 1))
		out.append(rec.recovery_window(start, stop, today))
		start = stop + timedelta(days=1)
	return out


def fence_rows(rows, filters, employees, companies) -> list:
	"""Employee / status filters and the HR company fence over planner rows. Pure.

	`employees`: {employee: {employee_name, company}}; `companies`: the fence,
	empty meaning unrestricted. A row whose employee is outside the fence is
	dropped, as Shift Attendance drops it inside its query.
	"""
	out = []
	for row in rows:
		info = employees.get(row.get("employee")) or {}
		if companies and info.get("company") not in companies:
			continue
		if filters.get("employee") and row.get("employee") != filters["employee"]:
			continue
		if filters.get("status") and row.get("status") != filters["status"]:
			continue
		out.append(
			{
				**row,
				"employee_name": row.get("employee_name") or info.get("employee_name"),
				"taps": cint(row.get("taps")),
			}
		)
	return out


def _employee_info(names) -> dict:
	if not names:
		return {}
	return {
		e.name: e
		for e in frappe.get_all(
			"Employee",
			filters={"name": ["in", sorted(names)]},
			fields=["name", "employee_name", "company"],
			limit_page_length=0,
		)
	}


def _rows(filters) -> list:
	today = getdate(now_datetime())
	families = [filters.family] if filters.get("family") else None
	rows = []
	for win in windows(filters.from_date, filters.to_date, today):
		rows.extend(rec.unclaimable_rows(win, families=families))
	employees = _employee_info({r.get("employee") for r in rows if r.get("employee")})
	fenced = fence_rows(rows, filters, employees, scoped_companies())
	logger.info("[unclaimable_days] %d row(s) detected, %d after filters and fence", len(rows), len(fenced))
	return fenced


def _summary(rows) -> str:
	counts = {status: sum(1 for r in rows if r.get("status") == status) for status in STATUSES}
	per_family = " · ".join(
		f"{family} {tally['detected']}" for family, tally in sorted(rec.family_counts(rows).items())
	)
	return _("Fixable {0} · On purpose {1} · Needs HR {2}{3}").format(
		counts[rec.STATUS_FIXABLE],
		counts[rec.STATUS_ON_PURPOSE],
		counts[rec.STATUS_NEEDS_HR],
		f" — {per_family}" if per_family else "",
	)


def _columns():
	def col(fieldname, label, fieldtype="Data", width=120, options=None):
		column = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
		if options:
			column["options"] = options
		return column

	return [
		col("employee_name", "Employee Name", width=180),
		col("employee", "Employee", "Link", 130, "Employee"),
		col("date", "Date", "Date", 100),
		col("shift", "Shift", width=150),
		col("family", "Family", width=70),
		col("reason", "Reason", width=420),
		col("status", "Status", width=100),
		col("attendance", "Attendance", "Link", 170, "Attendance"),
		col("taps", "Taps", "Int", 60),
	]
