"""Attendance-timezone resolution.

Attendance is a local wall-clock domain: "09:00 shift", "same day" and the
stale-session cutoff all mean local time where the employee physically works.
The site's System Settings timezone is a *different* clock — the system/audit
clock that accounting and integrations depend on. This module resolves the
former; call sites that stamp *when a system action happened* (approved_at,
rejected_at, sync watermarks) must keep using frappe's now_datetime().

Motivating case: the site runs Asia/Dubai while staff punch in from Malaysia
and China (UTC+8) — a 4h skew that made server-side "now" comparisons reject
valid check-outs and match the wrong shift.
"""

from __future__ import annotations

import logging
from datetime import datetime

import frappe
from frappe.utils import get_datetime_in_timezone, get_system_timezone, nowdate

logger = logging.getLogger(__name__)

_CACHE_ATTR = "_hrms_attendance_tz"


def _memo() -> dict:
	"""Request-scoped memo — the sweeper resolves the same handful of
	employees across hundreds of rows."""
	if not hasattr(frappe.local, _CACHE_ATTR):
		setattr(frappe.local, _CACHE_ATTR, {})
	return getattr(frappe.local, _CACHE_ATTR)


def _active_shift_location(employee: str) -> str | None:
	"""Shift Location of the employee's active assignment covering today.

	Date-granular on purpose: assignments are date-ranged, so resolving the
	date on the system clock is precise enough, and it avoids depending on the
	timezone we are in the middle of resolving.
	"""
	today = nowdate()
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Active",
			"start_date": ("<=", today),
			"shift_location": ("is", "set"),
		},
		or_filters=[["end_date", ">=", today], ["end_date", "is", "not set"]],
		fields=["shift_location"],
		order_by="start_date desc",
		limit=1,
	)
	return rows[0]["shift_location"] if rows else None


def get_attendance_timezone(employee: str | None, shift_location: str | None = None) -> str:
	"""Timezone whose wall clock this employee's attendance is measured in.

	Resolution order, most specific first:
	  1. Shift Location.timezone — where the employee physically punches.
	     Wins over the company because it is the truth about where the person
	     is standing (a UAE-registered company with staff working in Malaysia).
	     Resolved from the active assignment when the caller doesn't know it.
	  2. Company.hr_attendance_timezone — where the employee is registered.
	  3. System timezone — last resort; single-timezone sites keep today's
	     behaviour exactly.
	"""
	cached = _memo().get((employee, shift_location))
	if cached:
		return cached

	tz = None
	location = shift_location or (_active_shift_location(employee) if employee else None)
	if location:
		tz = frappe.db.get_value("Shift Location", location, "timezone")

	if not tz and employee:
		company = frappe.db.get_value("Employee", employee, "company")
		if company:
			tz = frappe.db.get_value("Company", company, "hr_attendance_timezone")

	if not tz:
		tz = get_system_timezone()
		logger.debug(
			"[timezone] Falling back to system timezone %s for employee=%s location=%s",
			tz,
			employee,
			location,
		)

	_memo()[(employee, shift_location)] = tz
	return tz


def employee_now(employee: str | None, shift_location: str | None = None) -> datetime:
	"""Naive 'now' in the employee's attendance timezone.

	Naive on purpose: stored check-in times are naive wall clock, so anything
	compared against them must share that basis. Mirrors frappe's own
	now_datetime(), which does exactly this for the system timezone.
	"""
	tz = get_attendance_timezone(employee, shift_location)
	return get_datetime_in_timezone(tz).replace(tzinfo=None)
