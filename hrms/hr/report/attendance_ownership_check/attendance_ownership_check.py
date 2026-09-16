"""Attendance Ownership Check — script report (Part A, 16 Sep 2026).

One row per live Attendance row in the window, with the verdict
`hrms.utils.attendance_ownership` reaches from the evidence: who owns it, why,
whether a relabel would give it its `auto_attendance` tick back, and what the
engine would mark if the day were rebuilt from its punches.

HR reads this BEFORE anything is written: the relabel switch ships off, and
this page is how HR decides whether to turn it on. Nothing here writes — the
"would be" column comes from the recovery's own dry-run preview
(`attendance_recovery._expected_on_rostered`), which computes on copies.

HR Manager and System Manager only, fenced to the caller's companies the way
Shift Attendance is (`report_scope.scoped_companies`): a Script Report runs its
own SQL and gets no row scope from the framework.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from hrms.utils import attendance_ownership as own
from hrms.utils.report_scope import scoped_companies

logger = logging.getLogger(__name__)

#: Where the window starts by default — the same floor the recovery repairs from.
START_FLOOR = date(2026, 8, 1)

#: Previews are computed per day; past this many rows the page shows the
#: verdicts alone rather than making HR wait for a preview nobody scrolls to.
PREVIEW_LIMIT = 150

OWNER_LABELS = {
	own.OWNER_HR: _("HR — a person wrote it"),
	own.OWNER_REQUEST: _("Leave or request"),
	own.OWNER_SYSTEM: _("System — automation made it"),
	own.OWNER_UNSURE: _("Unsure — treated as HR's"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_defaults(filters)
	logger.info("[attendance_ownership_check] execute filters=%s", dict(filters))
	rows = _rows(filters)
	return _columns(), rows, _summary(rows)


def _today() -> date:
	return getdate(now_datetime())


def _apply_defaults(filters) -> None:
	"""1 August → yesterday, where yesterday is a ceiling and not just a default.

	Today's shifts are still running: its rows would be judged on punches that
	have not arrived, and the preview would propose a rebuild from half a day.
	Filling in the blank was not enough — HR can type a date, and the picker
	offered today.
	"""
	yesterday = _today() - timedelta(days=1)
	if not filters.get("from_date"):
		filters["from_date"] = str(START_FLOOR)
	asked = getdate(filters["to_date"]) if filters.get("to_date") else yesterday
	filters["to_date"] = str(min(asked, yesterday))


def fence_rows(rows, filters, employees, companies) -> list:
	"""The company fence and the employee / owner filters over classified rows. Pure.

	`employees`: {employee: {employee_name, company}}; `companies`: the fence,
	empty meaning unrestricted. A row whose employee falls outside the fence is
	dropped, exactly as Shift Attendance drops it inside its own query.
	"""
	out = []
	for row in rows:
		info = employees.get(row.get("employee")) or {}
		if companies and info.get("company") not in companies:
			continue
		if filters.get("employee") and row.get("employee") != filters["employee"]:
			continue
		if filters.get("owner") and row.get("owner") != filters["owner"]:
			continue
		out.append(
			{
				**row,
				"employee_name": row.get("employee_name") or info.get("employee_name"),
				"owner_label": OWNER_LABELS.get(row.get("owner"), row.get("owner")),
				"would_relabel": _("yes") if row.get("would_relabel") else _("no"),
				"working_hours": flt(row.get("working_hours")),
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


def _expected_day(employee: str, day) -> dict:
	"""What the engine would mark for this employee-day. Reads only.

	Goes through the recovery's own dry-run preview, so the page cannot drift
	from what a rebuild would really do.
	"""
	from datetime import datetime, time

	from hrms.utils import attendance_recovery as rec

	day = getdate(day)
	assignments = rec._submitted_assignments(day, day)
	covering = [
		a
		for a in assignments
		if a.get("employee") == employee
		and getdate(a.get("start_date")) <= day
		and (not a.get("end_date") or getdate(a.get("end_date")) >= day)
	]
	times = rec._shift_times({a.get("shift_type") for a in covering if a.get("shift_type")})
	rostered = rec.rostered_shift(covering, times) or frappe.db.get_value(
		"Employee", employee, "default_shift"
	)
	if not rostered:
		return {"detail": "no shift is rostered for this day"}
	taps = rec._local_punches(
		employee, datetime.combine(day, time.min), datetime.combine(day + timedelta(days=1), time.min)
	)
	return rec._expected_on_rostered(employee, day, rostered, taps)


def preview_for(row) -> str:
	"""One line: the status, hours and shift a rebuild would write. Never raises."""
	try:
		expected = _expected_day(row.get("employee"), row.get("date")) or {}
	except Exception as exc:  # a preview is information, never a reason to fail the page
		logger.warning(
			"[attendance_ownership_check] no preview for %s on %s: %s",
			row.get("employee"),
			row.get("date"),
			exc,
		)
		# The reason is in the log above, not in a cell: a page is not the place
		# to print an internal identifier at whoever is reading it.
		return _("could not be previewed — see the error log")
	if not expected.get("status"):
		return expected.get("detail") or _("the rules would not mark this day")
	hours = flt(expected.get("working_hours"))
	return f"{expected['status']} · {hours}h · {expected.get('shift') or '?'}"


def _rows(filters) -> list:
	employees = [filters.employee] if filters.get("employee") else None
	classified = own.classify_window(filters.from_date, filters.to_date, employees=employees)
	info = _employee_info({r.get("employee") for r in classified if r.get("employee")})
	rows = fence_rows(classified, filters, info, scoped_companies())
	if len(rows) <= PREVIEW_LIMIT:
		for row in rows:
			row["preview"] = preview_for(row)
	else:
		logger.info("[attendance_ownership_check] %d row(s): previews left out", len(rows))
		for row in rows:
			row["preview"] = _("narrow the window to see what a rebuild would mark")
	logger.info(
		"[attendance_ownership_check] %d row(s) classified, %d after the filters and the fence",
		len(classified),
		len(rows),
	)
	return rows


def _summary(rows) -> str:
	counts = {owner: sum(1 for r in rows if r.get("owner") == owner) for owner in own.OWNERS}
	relabel = sum(1 for r in rows if r.get("would_relabel") == _("yes"))
	per_label = " · ".join(f"{OWNER_LABELS[owner]} {counts[owner]}" for owner in own.OWNERS)
	return _("{0} row(s) — {1} · {2} would get the automation tick back").format(
		len(rows), per_label, relabel
	)


def _columns():
	def col(fieldname, label, fieldtype="Data", width=120, options=None):
		column = {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width}
		if options:
			column["options"] = options
		return column

	return [
		col("employee_name", "Employee Name", width=170),
		col("employee", "Employee", "Link", 130, "Employee"),
		col("date", "Date", "Date", 100),
		col("status", "Status", width=90),
		col("working_hours", "Hours", "Float", 70),
		col("owner_label", "Owner", width=200),
		col("reason", "Why", width=380),
		col("would_relabel", "Would relabel", width=110),
		col("preview", "A rebuild would mark", width=240),
		col("attendance", "Attendance", "Link", 170, "Attendance"),
	]
