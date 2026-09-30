"""Rest Day Differences — who a one-rule rest day would move (30 Sep 2026).

Owner rulings, 30 Sep 2026 (docs/glass/plan/REST_DAY_RULE_PLAN.md): leave and
payroll will follow "the shift's calendar first, then the person's", as
overtime and absent marking already do. Step 0: before anything moves, show HR
who it moves. For each active employee and each date in the coming weeks, the
rest day by today's leave/payroll rule (the person's calendar) is compared with
the rest day by the one rule (the calendar of the shift they are on that date,
while it covers the date). This report writes nothing.

HR roles only, fenced to the caller's companies (`report_scope.fenced_companies`,
applied inside the query). The pure rules are pinned in
hrms/tests/test_rest_day_differences.py.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from hrms.utils.report_scope import fenced_companies

logger = logging.getLogger(__name__)

DEFAULT_WEEKS = 4
MAX_WEEKS = 12


def execute(filters=None):
	filters = frappe._dict(filters or {})
	weeks = max(1, min(cint(filters.get("weeks")) or DEFAULT_WEEKS, MAX_WEEKS))
	start = getdate(nowdate())
	end = start + timedelta(days=7 * weeks - 1)
	logger.info("[rest_day_differences] execute %s..%s filters=%s", start, end, dict(filters))
	rows = _rows(filters, start, end)
	if cint(filters.get("only_changed", 1)):
		rows = [r for r in rows if r["becomes_rest"] or r["becomes_work"]]
	return _columns(), rows, None, None, _summary(rows)


def shift_on(day: date, segments, default_shift):
	"""The shift a person is on for `day`. Pure.

	The Active assignment covering the day (open end = ongoing); of two that
	overlap, the one that started later (the newer decision). No assignment:
	the Employee's default shift. Neither: None, a roster gap.
	"""
	covering = [
		s
		for s in segments
		if getdate(s["start_date"]) <= day and (not s.get("end_date") or getdate(s["end_date"]) >= day)
	]
	if covering:
		return max(covering, key=lambda s: getdate(s["start_date"]))["shift_type"]
	return default_shift or None


def rest_day_changes(days, shift_of, shift_calendar, person_calendar, calendars):
	"""(becomes_rest, becomes_work): dates whose rest day differs between the
	person's calendar and the one rule. Pure.

	`calendars` maps a calendar name to {"span": (from, to), "rest": {dates}}.
	A shift calendar counts only while its span covers the date; a roster gap or
	a shift without a calendar keeps the person's calendar. A person with no
	calendar at all is not compared (alpha.26 already refuses them plainly).
	"""
	becomes_rest, becomes_work = [], []
	for day in days:
		mine = person_calendar(day)
		if not mine or mine not in calendars:
			continue
		ruled = mine
		shift_cal = shift_calendar.get(shift_of(day))
		if shift_cal in calendars:
			start, end = calendars[shift_cal]["span"]
			if start <= day <= end:
				ruled = shift_cal
		was_rest = day in calendars[mine]["rest"]
		now_rest = day in calendars[ruled]["rest"]
		if now_rest and not was_rest:
			becomes_rest.append(day)
		elif was_rest and not now_rest:
			becomes_work.append(day)
	return becomes_rest, becomes_work


def _rows(filters, start, end) -> list:
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	companies = fenced_companies(filters.get("company"))
	emp_filters = {"status": "Active"}
	if companies:
		emp_filters["company"] = ["in", companies]
	employees = frappe.get_all(
		"Employee",
		filters=emp_filters,
		fields=["name", "employee_name", "company", "branch", "department", "default_shift"],
		order_by="company, branch, employee_name",
	)
	if not employees:
		return []

	segments = {}
	for row in frappe.get_all(
		"Shift Assignment",
		filters={
			"docstatus": 1,
			"status": "Active",
			"employee": ["in", [e.name for e in employees]],
			"start_date": ["<=", end],
		},
		or_filters=[["end_date", "is", "not set"], ["end_date", ">=", start]],
		fields=["employee", "shift_type", "start_date", "end_date"],
	):
		segments.setdefault(row.employee, []).append(row)

	shift_calendar = {
		s.name: s.holiday_list for s in frappe.get_all("Shift Type", fields=["name", "holiday_list"])
	}
	days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
	cache = {}

	def calendar(name):
		if name and name not in cache:
			span = frappe.db.get_value("Holiday List", name, ["from_date", "to_date"])
			rest = frappe.get_all(
				"Holiday",
				filters={"parent": name, "holiday_date": ["between", [start, end]]},
				pluck="holiday_date",
			)
			cache[name] = {
				"span": (getdate(span[0]), getdate(span[1])) if span and all(span) else (date.max, date.min),
				"rest": {getdate(d) for d in rest},
			}
		return name

	rows = []
	for emp in employees:
		segs = segments.get(emp.name, [])
		for name in {shift_calendar.get(s.shift_type) for s in segs} | {
			shift_calendar.get(emp.default_shift)
		}:
			calendar(name)

		resolved = {}

		def mine(day, _emp=emp.name, _resolved=resolved):
			# A person's calendar changes only where one calendar's span ends and
			# another begins, so the resolver runs once and is reused while that
			# calendar still covers the date (review of fedf16621: per day it was
			# ~100k queries on a site with several hundred staff).
			if "calendar" in _resolved:
				cached = _resolved["calendar"]
				if cached is None:
					# no calendar at all: it will not appear mid-report
					return None
				start_, end_ = cache[cached]["span"]
				if start_ <= day <= end_:
					return cached
			name = calendar(get_holiday_list_for_employee(_emp, raise_exception=False, as_on=day))
			_resolved["calendar"] = name
			return name

		becomes_rest, becomes_work = rest_day_changes(
			days,
			shift_of=lambda day, _segs=segs, _default=emp.default_shift: shift_on(day, _segs, _default),
			shift_calendar=shift_calendar,
			person_calendar=mine,
			calendars=cache,
		)
		rows.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"becomes_rest": len(becomes_rest),
				"becomes_work": len(becomes_work),
				"rest_dates": ", ".join(d.strftime("%a %d %b") for d in becomes_rest),
				"work_dates": ", ".join(d.strftime("%a %d %b") for d in becomes_work),
				"shifts": ", ".join(sorted({s.shift_type for s in segs})) or emp.default_shift,
				"branch": emp.branch,
				"department": emp.department,
				"company": emp.company,
			}
		)
	logger.info(
		"[rest_day_differences] %d employee(s) checked, %d with a change",
		len(rows),
		sum(1 for r in rows if r["becomes_rest"] or r["becomes_work"]),
	)
	return rows


def _summary(rows) -> list:
	return [
		{
			"label": _("People affected"),
			"value": sum(1 for r in rows if r["becomes_rest"] or r["becomes_work"]),
			"datatype": "Int",
		},
		{
			"label": _("Days that become rest"),
			"value": sum(r["becomes_rest"] for r in rows),
			"datatype": "Int",
		},
		{
			"label": _("Days that become work"),
			"value": sum(r["becomes_work"] for r in rows),
			"datatype": "Int",
		},
	]


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
		col("becomes_rest", "Days that become rest", "Int", 150),
		col("rest_dates", "Dates that become rest", width=220),
		col("becomes_work", "Days that become work", "Int", 150),
		col("work_dates", "Dates that become work", width=220),
		col("shifts", "Shifts", width=180),
		col("branch", "Branch", "Link", 130, "Branch"),
		col("department", "Department", "Link", 150, "Department"),
		col("company", "Company", "Link", 150, "Company"),
	]
