"""Team-view member status — pure date/time logic, no Frappe imports.

One status per direct report per day, derived from what the manager needs to
see at a glance. Precedence:

1. punches or a present-ish Attendance doc → "Present" (facts beat filings —
   someone who punched in despite approved leave is present)
2. approved leave overlapping the day → "On Leave"
3. holiday with no activity → "Off"
4. future day → "Scheduled"
5. past day with nothing at all → "Absent"
6. today: "Not In Yet" until the shift has ended, then "Absent". No shift (or
   an overnight shift that ends tomorrow) keeps the benefit of the doubt.
"""

import logging
from datetime import date, time

logger = logging.getLogger(__name__)

PRESENT_ATTENDANCE = ("Present", "Work From Home", "Half Day")


def derive_member_status(
	day: date,
	today: date,
	now_time: time,
	on_leave: dict | None,
	is_holiday: bool,
	attendance_status: str | None,
	has_checkin: bool,
	shift_start: time | None,
	shift_end: time | None,
) -> str:
	if has_checkin or attendance_status in PRESENT_ATTENDANCE:
		return "Present"
	if on_leave:
		return "On Leave"
	if is_holiday:
		return "Off"
	if day > today:
		return "Scheduled"
	if day < today:
		return "Absent"
	# today, nothing recorded yet
	shift_has_ended = (
		shift_start is not None
		and shift_end is not None
		and shift_end > shift_start  # overnight shifts end tomorrow, never today
		and now_time > shift_end
	)
	status = "Absent" if shift_has_ended else "Not In Yet"
	logger.debug(
		"[team_status] day=%s now=%s shift=%s-%s -> %s", day, now_time, shift_start, shift_end, status
	)
	return status
