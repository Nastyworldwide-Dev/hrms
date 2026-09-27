"""Roster Patterns — how each person is really rostered (alpha.14, 27 Sep 2026).

The roster is being designed as a new feature, and the owner ruled "no
guesswork": nothing on hand says how many people work a fixed shift, a weekly
rota, a rotation or day by day. This report answers that from the live
Shift Assignments of the last full weeks, and writes nothing.

HR roles only, fenced to the caller's companies (`report_scope.fenced_companies`,
applied inside the query). Pure rules — days_rostered, classify, weekday_label,
source — are pinned in hrms/tests/test_roster_patterns.py.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from hrms.utils.report_scope import fenced_companies

logger = logging.getLogger(__name__)

DEFAULT_WEEKS = 8
MAX_WEEKS = 26
#: a rotation holds each shift at least a week before changing
ROTATION_BLOCK_DAYS = 7
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
SOURCES = ("By hand", "Weekly schedule", "Location rule")
FIXED, WEEKLY, ROTATING, DAY_BY_DAY = "Fixed", "Weekly", "Rotating", "Day by day"
DEFAULT_ONLY, NO_SHIFT = "Default shift only", "No shift"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start, end = window(getdate(nowdate()), cint(filters.get("weeks")) or DEFAULT_WEEKS)
	logger.info("[roster_patterns] execute %s..%s filters=%s", start, end, dict(filters))
	rows = _rows(filters, start, end)
	return _columns(), rows, None, None, _summary(rows)


def window(today: date, weeks: int) -> tuple[date, date]:
	"""The last `weeks` full Monday–Sunday weeks before today. Pure."""
	weeks = max(1, min(weeks, MAX_WEEKS))
	end = today - timedelta(days=today.weekday() + 1)
	return end - timedelta(days=7 * weeks - 1), end


def days_rostered(segments, start: date, end: date) -> dict:
	"""{date: shift_type} for every rostered day inside [start, end]. Pure.
	An open-ended assignment runs to the end of the window; a later one wins."""
	days = {}
	for row in sorted(segments, key=lambda r: getdate(r["start_date"])):
		d = max(getdate(row["start_date"]), start)
		stop = min(getdate(row["end_date"]) if row.get("end_date") else end, end)
		while d <= stop:
			days[d] = row["shift_type"]
			d += timedelta(days=1)
	return days


def classify(days: dict, start: date, end: date) -> str:
	"""Fixed / Weekly / Rotating / Day by day, or "" when nothing is rostered. Pure."""
	if not days:
		return ""
	ordered = sorted(days)
	first, last = ordered[0], ordered[-1]
	runs = _runs(days, ordered)
	unbroken = last == end and len(days) == (end - first).days + 1
	# one shift throughout, or one move to a new shift for good
	if unbroken and len(runs) <= 2:
		return FIXED
	if _same_every_week(days, first, last, start, end):
		return WEEKLY
	# a rotation comes back to a shift it held before, a week or more at a time
	returns = len({days[run[0]] for run in runs}) < len(runs)
	if returns and _held_in_blocks(runs, start, end):
		return ROTATING
	return DAY_BY_DAY


def _same_every_week(days, first, last, start, end) -> bool:
	monday = first - timedelta(days=first.weekday())
	weeks = []
	while monday <= last:
		if monday >= start and monday + timedelta(days=6) <= end:
			week = [monday + timedelta(days=n) for n in range(7)]
			weeks.append(tuple((d.weekday(), days[d]) for d in week if d in days))
		monday += timedelta(days=7)
	return len(weeks) >= 2 and all(weeks) and len(set(weeks)) == 1


def _runs(days, ordered) -> list:
	"""Consecutive days on the same shift; a gap or a change starts a new run."""
	runs, current = [], [ordered[0]]
	for d in ordered[1:]:
		if days[d] == days[current[0]] and (d - current[-1]).days == 1:
			current.append(d)
		else:
			runs.append(current)
			current = [d]
	runs.append(current)
	return runs


def _held_in_blocks(runs, start, end) -> bool:
	for run in runs:
		clipped = run[0] == start or run[-1] == end
		if not clipped and (run[-1] - run[0]).days + 1 < ROTATION_BLOCK_DAYS:
			return False
	return True


def weekday_label(weekdays: set) -> str:
	"""Mon–Fri, Every day, or Mon, Wed, Fri. Pure."""
	if not weekdays:
		return ""
	if len(weekdays) == 7:
		return _("Every day")
	ordered = sorted(weekdays)
	if len(ordered) >= 3 and ordered[-1] - ordered[0] == len(ordered) - 1:
		return f"{WEEKDAYS[ordered[0]]}–{WEEKDAYS[ordered[-1]]}"
	return ", ".join(WEEKDAYS[n] for n in ordered)


def source(segments) -> str:
	"""Where the rows came from: by hand, a weekly schedule, or a location rule. Pure."""
	found = set()
	for row in segments:
		if row.get("created_by_shift_rule"):
			found.add("Location rule")
		elif row.get("shift_schedule_assignment"):
			found.add("Weekly schedule")
		else:
			found.add("By hand")
	return ", ".join(s for s in SOURCES if s in found)


def _rows(filters, start, end) -> list:
	companies = fenced_companies(filters.get("company"))
	emp_filters = {"status": "Active"}
	if companies:
		emp_filters["company"] = ["in", companies]
	if filters.get("branch"):
		emp_filters["branch"] = filters["branch"]
	employees = frappe.get_all(
		"Employee",
		filters=emp_filters,
		fields=[
			"name",
			"employee_name",
			"company",
			"branch",
			"department",
			"shift_location",
			"default_shift",
			"reports_to",
		],
		order_by="company, branch, employee_name",
	)
	if not employees:
		return []
	by_employee = {}
	for row in frappe.get_all(
		"Shift Assignment",
		filters={
			"docstatus": 1,
			"status": "Active",
			"employee": ["in", [e.name for e in employees]],
			"start_date": ["<=", end],
		},
		or_filters=[["end_date", "is", "not set"], ["end_date", ">=", start]],
		fields=[
			"employee",
			"shift_type",
			"start_date",
			"end_date",
			"created_by_shift_rule",
			"shift_schedule_assignment",
		],
	):
		by_employee.setdefault(row.employee, []).append(row)
	leaders = {e.name: e.employee_name for e in employees}
	return [_row(e, by_employee.get(e.name, []), leaders, start, end) for e in employees]


def _row(emp, segments, leaders, start, end) -> dict:
	days = days_rostered(segments, start, end)
	pattern = classify(days, start, end) or (DEFAULT_ONLY if emp.default_shift else NO_SHIFT)
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"company": emp.company,
		"branch": emp.branch,
		"department": emp.department,
		"shift_location": emp.shift_location,
		"pattern": pattern,
		"shifts": ", ".join(sorted(set(days.values()))) or emp.default_shift,
		"weekdays": weekday_label({d.weekday() for d in days}),
		"days_rostered": len(days),
		"pieces": len(segments),
		"source": source(segments),
		"reports_to": leaders.get(emp.reports_to) or emp.reports_to,
	}


def _summary(rows) -> list:
	counts = Counter(r["pattern"] for r in rows)
	order = (FIXED, WEEKLY, ROTATING, DAY_BY_DAY, DEFAULT_ONLY, NO_SHIFT)
	return [{"label": _(p), "value": counts[p], "datatype": "Int"} for p in order if counts[p]]


def _columns():
	def col(fieldname, label, fieldtype="Data", width=140, options=None):
		return {
			"fieldname": fieldname,
			"label": _(label),
			"fieldtype": fieldtype,
			"width": width,
			"options": options,
		}

	return [
		col("employee", "Employee", "Link", 130, "Employee"),
		col("employee_name", "Name", width=180),
		col("pattern", "Pattern", width=140),
		col("shifts", "Shifts", width=200),
		col("weekdays", "Days", width=130),
		col("days_rostered", "Rostered days", "Int", 110),
		col("pieces", "Assignments", "Int", 110),
		col("source", "Set by", width=160),
		col("branch", "Branch", "Link", 130, "Branch"),
		col("shift_location", "Shift Location", "Link", 150, "Shift Location"),
		col("department", "Department", "Link", 150, "Department"),
		col("reports_to", "Reports to", width=160),
		col("company", "Company", "Link", 150, "Company"),
	]
