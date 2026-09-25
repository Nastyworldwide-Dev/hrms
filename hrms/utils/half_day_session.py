"""Which half of the day a half-day leave takes (owner ruling, 25 Sep 2026).

A person on a morning half day who walks in at lunch is not late, and one on
an afternoon half day who leaves at lunch did not leave early. The boundary is
the middle of THEIR shift occurrence, so a night shift's middle falls after
midnight. A half day filed without a session (everything before this release)
keeps the old whole-shift rule; nothing is guessed.
"""

import logging

logger = logging.getLogger(__name__)

SESSIONS = ("AM", "PM")


def _midpoint(shift_start, shift_end):
	return shift_start + (shift_end - shift_start) / 2


def late_early_bounds(shift_start, shift_end, session):
	"""(day starts, day ends) for late/early marking. Pure."""
	if session not in SESSIONS or not (shift_start and shift_end):
		return shift_start, shift_end
	middle = _midpoint(shift_start, shift_end)
	return (middle, shift_end) if session == "AM" else (shift_start, middle)


def session_hint(shift_start, shift_end, session):
	"""(clock, sentence) the employee reads under the AM | PM choice. Pure."""
	if session not in SESSIONS or not (shift_start and shift_end):
		return None, ""
	clock = _midpoint(shift_start, shift_end).strftime("%H:%M")
	if session == "AM":
		return clock, f"Off in the morning. Start by {clock}."
	return clock, f"Off in the afternoon. Leave at {clock}."


def hints_for(shift_start, shift_end):
	"""What the leave form shows under AM | PM, for one shift occurrence. Pure."""
	if not (shift_start and shift_end):
		return {
			"midpoint": None,
			"shift": None,
			"AM": "Off in the morning.",
			"PM": "Off in the afternoon.",
			"AM_short": "",
			"PM_short": "",
		}
	clock, am = session_hint(shift_start, shift_end, "AM")
	_, pm = session_hint(shift_start, shift_end, "PM")
	span = f"{shift_start.strftime('%H:%M')}–{shift_end.strftime('%H:%M')}"
	return {
		"midpoint": clock,
		"shift": span,
		"AM": am,
		"PM": pm,
		# what fits the form row once chosen (iOS keeps a picked value short)
		"AM_short": f"start {clock}",
		"PM_short": f"leave {clock}",
	}


def flags_for(in_time, out_time, shift_start, shift_end, session, late_grace, early_grace, late_on, early_on):
	"""late_entry / early_exit for a day, against the half's line. Pure.

	The same comparison ShiftType.get_attendance makes, so a day marked before
	the leave was approved ends with the flags a day marked after it would."""
	from datetime import timedelta

	day_starts, day_ends = late_early_bounds(shift_start, shift_end, session)
	late = bool(
		late_on and in_time and day_starts and in_time > day_starts + timedelta(minutes=late_grace or 0)
	)
	early = bool(
		early_on and out_time and day_ends and out_time < day_ends - timedelta(minutes=early_grace or 0)
	)
	return {"late_entry": int(late), "early_exit": int(early)}


def late_early_for_row(attendance, session):
	"""The flags an existing Attendance row should carry under `session`.

	Reads the row's shift occurrence; a row with no shift or no times keeps
	its flags (nothing to measure against, nothing guessed)."""
	import frappe
	from frappe.utils import cint, get_datetime

	if not attendance.get("shift") or not (attendance.get("in_time") or attendance.get("out_time")):
		return {}
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details

	anchor = get_datetime(attendance.get("in_time") or attendance.get("out_time"))
	details = get_shift_details(attendance.shift, anchor)
	if not details:
		return {}
	shift = frappe.get_cached_doc("Shift Type", attendance.shift)
	out = flags_for(
		in_time=attendance.get("in_time") and get_datetime(attendance.in_time),
		out_time=attendance.get("out_time") and get_datetime(attendance.out_time),
		shift_start=details.start_datetime,
		shift_end=details.end_datetime,
		session=session,
		late_grace=cint(shift.late_entry_grace_period),
		early_grace=cint(shift.early_exit_grace_period),
		late_on=cint(shift.enable_late_entry_marking),
		early_on=cint(shift.enable_early_exit_marking),
	)
	logger.info(
		"[half_day_session] %s %s under %s: %s",
		attendance.get("name"),
		attendance.get("attendance_date"),
		session,
		out,
	)
	return out


def session_problem(half_day, session, is_new):
	"""'missing' when a NEW half day names no half. Pure.

	Requests saved before this release keep a blank session; they are never
	refused on edit or approval for a field that did not exist.
	"""
	if half_day and is_new and session not in SESSIONS:
		return "missing"
	return None


def sessions_clash(mine, theirs):
	"""Two half days on one date: True same half, False AM+PM, None unknown. Pure."""
	if mine not in SESSIONS or theirs not in SESSIONS:
		return None
	return mine == theirs


def approved_session(employee, day):
	"""The session of an APPROVED half-day leave on `day`, or None."""
	import frappe

	rows = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Approved",
			"half_day": 1,
			"half_day_date": day,
		},
		pluck="half_day_session",
	)
	sessions = {row for row in rows if row in SESSIONS}
	# AM + PM on one date is a whole day off, not a half: no boundary moves.
	session = sessions.pop() if len(sessions) == 1 else None
	if session:
		logger.info("[half_day_session] %s on %s is off in the %s", employee, day, session)
	return session
