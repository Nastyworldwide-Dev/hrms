# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Home's "This week" and "Coming up" blocks (owner-approved Home, 23 Sep 2026).

Session-scoped by construction: no endpoint takes an employee. Both always
answer, even when empty, so the block can say WHY it is empty rather than
vanish.

NOTHING HERE IS NEW OVERTIME ARITHMETIC. "Overtime to claim" is the figure the
Requests screen already shows (requests_summary._overtime); a second
implementation would be a second answer.

"Coming up" never carries a reason: a leave type, a training name, the word
"Trip" and a date. The description, purpose or reason fields are never read.
"""

import logging
import re
from datetime import timedelta

import frappe
from frappe.utils import flt, getdate

from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

#: Attendance statuses that mean the employee worked that day.
WORKED_STATUSES = ["Present", "Half Day"]


def _employee() -> str:
	from hrms.api import get_current_employee

	return get_current_employee()


def _today(employee: str):
	"""Today on the EMPLOYEE's clock, not the server's."""
	return employee_now(employee).date()


def _paired_days(employee: str, start, end) -> set:
	"""Dates in [start, end] holding an IN followed later that day by an OUT."""
	punches = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ("between", [f"{start} 00:00:00", f"{end} 23:59:59"]),
		},
		fields=["time", "log_type"],
		order_by="time asc",
		ignore_permissions=True,
	)
	open_in, days = set(), set()
	for row in sorted(punches, key=lambda r: r.time):
		day = getdate(row.time)
		if row.log_type == "IN":
			open_in.add(day)
		elif row.log_type == "OUT" and day in open_in:
			days.add(day)
	return days


@frappe.whitelist(methods=["GET", "POST"])
def get_home_week() -> dict:
	"""Days worked Monday..today and overtime not yet claimed, for the caller."""
	from hrms.api.requests_summary import _overtime

	employee = _employee()
	today = _today(employee)
	monday = today - timedelta(days=today.weekday())
	worked = {
		getdate(value)
		for value in frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"docstatus": 1,
				"status": ("in", WORKED_STATUSES),
				"attendance_date": ("between", [monday, today]),
			},
			pluck="attendance_date",
			ignore_permissions=True,
		)
	}
	worked |= _paired_days(employee, monday, today)
	overtime = flt((_overtime() or {}).get("unclaimed_hours"))
	logger.info(
		"[home] week employee=%s from=%s to=%s days=%d ot=%.2f",
		employee,
		monday,
		today,
		len(worked),
		overtime,
	)
	return {
		"from_date": str(monday),
		"to_date": str(today),
		"days_worked": len(worked),
		"overtime_hours": overtime,
	}


def _holiday_list(employee: str, today) -> str | None:
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	return get_holiday_list_for_employee(employee, raise_exception=False, as_on=today)


def _next_leave(employee: str, today) -> dict | None:
	rows = frappe.get_all(
		"Leave Application",
		filters={"employee": employee, "status": "Approved", "docstatus": 1, "from_date": (">=", today)},
		fields=["leave_type", "from_date"],
		order_by="from_date asc",
		limit=1,
		ignore_permissions=True,
	)
	return (
		{"kind": "leave", "label": rows[0].leave_type, "date": str(getdate(rows[0].from_date))}
		if rows
		else None
	)


def _next_trip(employee: str, today) -> dict | None:
	if not frappe.db.exists("DocType", "Travel Request"):
		return None
	names = frappe.get_all(
		"Travel Request",
		filters={"employee": employee, "docstatus": 1},
		pluck="name",
		ignore_permissions=True,
	)
	if not names:
		return None
	legs = frappe.get_all(
		"Travel Itinerary",
		filters={
			"parenttype": "Travel Request",
			"parent": ("in", names),
			"departure_date": (">=", f"{today} 00:00:00"),
		},
		fields=["departure_date"],
		order_by="departure_date asc",
		limit=1,
		ignore_permissions=True,
	)
	return {"kind": "travel", "label": "Trip", "date": str(getdate(legs[0].departure_date))} if legs else None


def _next_training(employee: str, today) -> dict | None:
	if not frappe.db.exists("DocType", "Training Event"):
		return None
	events = sorted(
		{
			row.parent
			for row in frappe.get_all(
				"Training Event Employee",
				filters={"parenttype": "Training Event", "employee": employee},
				fields=["parent"],
				ignore_permissions=True,
			)
		}
	)
	if not events:
		return None
	rows = frappe.get_all(
		"Training Event",
		filters={
			"name": ("in", events),
			"docstatus": 1,
			"event_status": ("!=", "Cancelled"),
			"start_time": (">=", f"{today} 00:00:00"),
		},
		fields=["event_name", "start_time"],
		order_by="start_time asc",
		limit=1,
		ignore_permissions=True,
	)
	if not rows:
		return None
	return {"kind": "training", "label": rows[0].event_name, "date": str(getdate(rows[0].start_time))}


def _next_holiday(employee: str, today) -> dict | None:
	holiday_list = _holiday_list(employee, today)
	if not holiday_list:
		return None
	rows = frappe.get_all(
		"Holiday",
		filters={"parent": holiday_list, "weekly_off": 0, "holiday_date": (">=", today)},
		fields=["holiday_date", "description"],
		order_by="holiday_date asc",
		limit=1,
		ignore_permissions=True,
	)
	if not rows:
		return None
	# Holiday.description is a Text Editor field: its NAME, wrapped in HTML.
	label = re.sub(r"<[^>]+>", "", rows[0].description or "").strip()
	return {"label": label, "date": str(getdate(rows[0].holiday_date))}


@frappe.whitelist(methods=["GET", "POST"])
def get_home_coming_up() -> dict:
	"""The caller's next booked thing, and the next public holiday as a fallback."""
	employee = _employee()
	today = _today(employee)
	booked = [
		item
		for item in (
			_next_leave(employee, today),
			_next_trip(employee, today),
			_next_training(employee, today),
		)
		if item
	]
	# Earliest wins; on a tie the order above (leave, trip, training) decides.
	upcoming = min(booked, key=lambda item: item["date"]) if booked else None
	holiday = _next_holiday(employee, today)
	logger.info(
		"[home] coming-up employee=%s next=%s holiday=%s",
		employee,
		upcoming and upcoming["kind"],
		bool(holiday),
	)
	return {"next": upcoming, "holiday": holiday}
