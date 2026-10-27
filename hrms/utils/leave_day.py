"""What approved leave leaves of a person's day: the one reading every person-facing feature uses.

Owner, 27 Oct 2026: the app "isn't really intelligent" — it reminded people on approved leave to
check in, and Home told them "Not checked in". Each feature read leave its own way, or not at all.
This is the one place that answers "is this day off, or which half is". One batched read per day.

Rules (owner rulings 25 Sep + 27 Oct 2026):
- Any full-day approved row, or an AM half and a PM half together, is a whole day off.
- A half day is read from its half_day_date, or from a one-day leave's only day; a multi-day
  leave marked half day with no date is not guessed: its days are full days off.
"""

from __future__ import annotations

import frappe
from frappe.utils import getdate

SESSIONS = ("AM", "PM")


def approved_leave(employees, day):
	"""Approved, submitted leave covering `day` for these employees (one read)."""
	return frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			"employee": ["in", list(employees)],
			"from_date": ["<=", day],
			"to_date": [">=", day],
		},
		fields=[
			"employee",
			"leave_type",
			"half_day",
			"half_day_date",
			"half_day_session",
			"from_date",
			"to_date",
		],
		limit_page_length=0,
	)


def half_on(row, day):
	"""Is `day` the half day of this leave row?"""
	if not row.get("half_day"):
		return False
	half = row.get("half_day_date") or (
		row.get("from_date") if row.get("from_date") == row.get("to_date") else None
	)
	return half is not None and getdate(half) == getdate(day)


def off_session(rows, day):
	"""None for a whole day off, else the half that is off ("AM"/"PM")."""
	sessions = set()
	for row in rows:
		session = row.get("half_day_session") if half_on(row, day) else None
		if session not in SESSIONS:
			return None
		sessions.add(session)
	return sessions.pop() if len(sessions) == 1 else None


def by_employee(employees, day):
	"""{employee: [approved leave rows covering day]} for these employees."""
	out = {}
	for row in approved_leave(employees, day):
		out.setdefault(row.employee, []).append(row)
	return out


def full_day_leave(employee, day):
	"""The leave type when `employee` is off all of `day` on approved leave, else None."""
	rows = by_employee([employee], day).get(employee)
	if not rows or off_session(rows, day):
		return None
	return rows[0].get("leave_type")
