"""Days a leave or attendance request already speaks for.

Owner ruling (15 Sep 2026): the system never resolves a day to Absent on its
own while a Leave Application exists for it in any non-rejected state, and an
approved leave is counted as what it is. An OPEN leave has no Attendance row
yet (only approval writes one), so every reader that judged a day by its rows
— the hourly Absent marker, the recovery planners, the "days you can claim"
list — saw nothing and treated the day as the automation's to resolve.

This is the one supplier they all ask. Rejected and cancelled requests cover
nothing; an Attendance Request (work from home / on duty) awaiting a decision
holds the day the same way.
"""

import logging
from datetime import timedelta

import frappe
from frappe.utils import getdate

logger = logging.getLogger(__name__)

#: Leave Application and Attendance Request share these decision states.
LIVE_STATES = ["Open", "Approved"]


def request_covered_days(employee: str, start, end) -> dict:
	"""{day: reason} for every day in [start, end] a live Leave Application or
	Attendance Request of `employee` covers. The reason names the document."""
	start, end = getdate(start), getdate(end)
	covered: dict = {}
	for doctype in ("Leave Application", "Attendance Request"):
		rows = frappe.get_all(
			doctype,
			filters={
				"employee": employee,
				"docstatus": ["<", 2],
				"status": ["in", list(LIVE_STATES)],
				"from_date": ["<=", end],
				"to_date": [">=", start],
			},
			fields=["name", "status", "from_date", "to_date"],
		)
		for row in rows:
			day = max(getdate(row.from_date), start)
			last = min(getdate(row.to_date), end)
			while day <= last:
				covered.setdefault(day, f"{doctype} {row.name} ({row.status}) covers it")
				day += timedelta(days=1)
	if covered:
		logger.info(
			"[leave_cover] %s: %d day(s) between %s and %s held by a leave or attendance request",
			employee,
			len(covered),
			start,
			end,
		)
	return covered
