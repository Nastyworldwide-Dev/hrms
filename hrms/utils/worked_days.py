# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Which days the punches say were worked — ONE rule (owner bug, 23 Sep 2026).

A day is worked when it has a submitted Present / Half Day Attendance, or an
IN followed later that day by an OUT. Home counted the second half and the
Calendar did not, so a finished day read "worked" on Home and blank on the
Calendar until auto-attendance ran. Both now read the punches here.
"""

import logging

import frappe
from frappe.utils import getdate

logger = logging.getLogger(__name__)


def punch_days(employee: str, start, end) -> tuple[set, set]:
	"""(paired, open) dates in [start, end].

	paired: an IN followed later that day by an OUT.
	open:   the day's last punch is an IN — somebody is still at work, or forgot
	        to check out. A lone OUT is neither.
	"""
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
	open_in, paired, last = set(), set(), {}
	for row in sorted(punches, key=lambda r: r.time):
		day = getdate(row.time)
		last[day] = row.log_type
		if row.log_type == "IN":
			open_in.add(day)
		elif row.log_type == "OUT" and day in open_in:
			paired.add(day)
	open_days = {day for day, log_type in last.items() if log_type == "IN"}
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
	"""Dates in [start, end] holding an IN followed later that day by an OUT."""
	return punch_days(employee, start, end)[0]
