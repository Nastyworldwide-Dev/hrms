"""Missed Check-outs After Midnight — script report (alpha.10, 25 Sep 2026).

Before alpha.10 the phone gave up on a check-in after 16 hours and showed
"Check in" again at about 12 am / 3 am to people still working (employee
report, 25 Sep 2026). Their tap was saved as a SECOND check-in, so the day
has two INs and no OUT, and its hours are wrong.

This lists those days so HR can fix each one with Fix a day, using the real
check-out time. It only READS: the system cannot know when the person really
left, so nothing is changed automatically (owner, 25 Sep 2026).

A day is listed when an IN is followed, between 00:00 and 06:00 the next
morning, by another IN with no OUT between them. HR Manager / System Manager,
fenced to the caller's companies like the other HR reports.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

from hrms.utils.report_scope import scoped_companies

logger = logging.getLogger(__name__)

#: The attendance repair floor: nothing before it is in scope.
START_FLOOR = date(2026, 8, 1)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date = getdate(filters.get("from_date") or START_FLOOR)
	to_date = getdate(filters.get("to_date") or (getdate() - timedelta(days=1)))
	logger.info("[missed_checkouts] %s..%s employee=%s", from_date, to_date, filters.get("employee"))
	return _columns(), _rows(from_date, to_date, filters.get("employee"))


def _columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "day", "label": _("Work day"), "fieldtype": "Date", "width": 110},
		{"fieldname": "first_in", "label": _("Checked in"), "fieldtype": "Datetime", "width": 160},
		{
			"fieldname": "second_in",
			"label": _("Tapped again (saved as a check-in)"),
			"fieldtype": "Datetime",
			"width": 220,
		},
		{
			"fieldname": "suggested_out",
			"label": _("Suggested check-out (confirm it)"),
			"fieldtype": "Datetime",
			"width": 200,
		},
		{"fieldname": "what_to_do", "label": _("What to do"), "fieldtype": "Data", "width": 420},
	]


def _rows(from_date, to_date, employee=None):
	filters = {
		"time": ["between", [f"{from_date} 00:00:00", f"{to_date + timedelta(days=1)} 06:00:00"]],
		"log_type": ["in", ["IN", "OUT"]],
		"skip_auto_attendance": 0,
	}
	if employee:
		filters["employee"] = employee
	companies = scoped_companies()
	if companies:
		filters["employee"] = ["in", frappe.get_all("Employee", {"company": ["in", companies]}, pluck="name")]
	punches = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["employee", "employee_name", "time", "log_type", "remote_approval_status"],
		order_by="employee asc, time asc",
	)
	return list(find_missed(punches, from_date, to_date))


def find_missed(punches, from_date, to_date):
	"""Yield one row per IN whose next punch is an IN between 00:00 and 06:00
	the following morning. Pure over the punch rows (tested bench-free)."""
	previous = None
	for row in punches:
		if row.get("remote_approval_status") == "Rejected":
			continue
		if (
			previous
			and previous["employee"] == row["employee"]
			and previous["log_type"] == "IN"
			and row["log_type"] == "IN"
		):
			first, again = get_datetime(previous["time"]), get_datetime(row["time"])
			if (
				again.date() == first.date() + timedelta(days=1)
				and again.hour < 6
				and from_date <= first.date() <= to_date
			):
				yield {
					"employee": row["employee"],
					"employee_name": row.get("employee_name"),
					"day": first.date(),
					"first_in": first,
					"second_in": again,
					# alpha.11: a SUGGESTION, never applied here. The tap the old
					# button saved as a check-in is the likeliest real check-out;
					# only HR, who can ask the person, confirms it.
					"suggested_out": again,
					"what_to_do": _(
						"Tick the row, press Punches, then Fix attendance: tick the {0} tap as the "
						"check-out if the person confirms that is when they left, or type the real time."
					).format(again.strftime("%H:%M")),
				}
		previous = row
