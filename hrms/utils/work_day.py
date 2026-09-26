"""Which day a tap belongs to: the day its session started (owner, 26 Sep 2026).

The attendance engine already books a session to the day its shift started,
past midnight included. The Calendar and the Team page read taps by CLOCK
date, so a 01:41 check-out showed on the next day by itself ("In progress",
"IN — OUT 01:41") and looked like a day nobody checked out of. One rule here:
a tap's work day is its shift's start date; a tap with no shift follows the
check-in it closes. A tap that crossed midnight carries `next_day`, and the
clock date lists where it was counted, so both screens say it plainly.
"""

import logging
from datetime import timedelta

from frappe.utils import get_datetime, getdate

logger = logging.getLogger(__name__)


def work_day(tap, open_day=None):
	"""The day this tap counts on. Pure."""
	if tap.get("shift_start"):
		return getdate(tap["shift_start"])
	when = get_datetime(tap["time"])
	# a check-out closes the session its check-in opened, whatever the clock says
	if tap.get("log_type") == "OUT" and open_day and when.date() == open_day + timedelta(days=1):
		return open_day
	return when.date()


def taps_for_day(taps, day):
	"""(taps that count on `day`, taps clocked on `day` but counted elsewhere).
	`taps` is every tap from the day before to the day after, in time order."""
	day = getdate(day)
	mine, elsewhere = [], []
	open_day = None
	for tap in taps:
		counted = work_day(tap, open_day)
		when = get_datetime(tap["time"])
		if tap.get("log_type") == "IN":
			open_day = counted
		elif tap.get("log_type") == "OUT":
			open_day = None
		if counted == day:
			mine.append({**tap, "next_day": when.date() > counted})
		elif when.date() == day:
			elsewhere.append({"time": str(when), "log_type": tap.get("log_type"), "counted_on": str(counted)})
	logger.debug("[work_day] %s: %d tap(s) count here, %d counted elsewhere", day, len(mine), len(elsewhere))
	return mine, elsewhere
