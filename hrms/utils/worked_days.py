# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Which days the punches say were worked — ONE rule (owner bug, 23 Sep 2026).

A day is worked when it has a submitted Present / Half Day Attendance, or an
IN followed later that day by an OUT. Home counted the second half and the
Calendar did not, so a finished day read "worked" on Home and blank on the
Calendar until auto-attendance ran. Both now read the punches here.
"""

import logging
from datetime import timedelta

import frappe
from frappe.utils import get_datetime, getdate

logger = logging.getLogger(__name__)

#: Longest IN->OUT span still read as one shift.
MAX_SHIFT = timedelta(hours=24)


def punch_days(employee: str, start, end) -> tuple[set, set]:
	"""(paired, open) dates in [start, end].

	paired: an IN followed by the next OUT, credited to the day the IN was on.
	        A night shift (IN 22:00, OUT 06:00 next morning) is ONE worked day,
	        the day it began — so the read runs one day past `end` to find the
	        OUT that closes the last day's shift.
	open:   the last punch is an IN with no OUT after it — somebody is still at
	        work, or forgot to check out. A lone OUT is neither.
	"""
	punches = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ("between", [f"{start} 00:00:00", f"{getdate(end) + timedelta(days=1)} 23:59:59"]),
		},
		fields=["time", "log_type", "shift_start"],
		order_by="time asc",
		ignore_permissions=True,
	)
	from hrms.utils.work_day import work_day

	paired, open_in, open_at = set(), None, None
	for row in sorted(punches, key=lambda r: r.time):
		if row.log_type == "IN":
			# the WORK day (hrms/utils/work_day.py), the one rule every screen
			# and the attendance record use: the shift's start date
			open_in, open_at = work_day(row), get_datetime(row.time)
		elif row.log_type == "OUT" and open_in is not None:
			# A shift is under a day long. An IN left open for days that meets
			# a later OUT is a forgotten check-out, not a worked day.
			if get_datetime(row.time) - open_at <= MAX_SHIFT:
				paired.add(open_in)
			open_in = None
	start, end = getdate(start), getdate(end)
	paired = {day for day in paired if start <= day <= end}
	open_days = {open_in} if open_in is not None and start <= open_in <= end else set()
	logger.debug(
		"[worked_days] employee=%s %s..%s punches=%d paired=%d open=%d",
		employee,
		start,
		end,
		len(punches),
		len(paired),
		len(open_days),
	)
	return paired, open_days

def paired_days(employee: str, start, end) -> set:
	"""Dates in [start, end] whose shift (IN, then the next OUT) began that day."""
	return punch_days(employee, start, end)[0]
