# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""What is true for this employee RIGHT NOW (PWA Home, revamp §2).

Home's first line said "Last check-out was at 08:17 pm" and left the reader to
work out the rest: am I on shift, have I been in for six hours or nine, does
today's shift even start yet. A person standing at a door with a phone in one
hand should not be doing arithmetic.

So this answers the three things the top of Home actually states — the shift
window, whether a session is open, and how long it has been running — as ONE
call, because Home already makes several and a fourth spinner at the top of
the first screen is the worst place to add latency.

Session-scoped by construction: no endpoint takes an employee.
"""

import logging

import frappe
from frappe.utils import flt, get_datetime

logger = logging.getLogger(__name__)


def _open_session(employee, now):
	"""The newest IN with no OUT after it, while its session is still open.

	The SAME rule the check-in button and the punch use
	(remote_checkin.session_open_until: 06:00 the next morning, or the
	shift's check-out window if later). It was a separate 16-hour cap, so
	after 16 h Home dropped the timer and the button offered Check in while
	the person was still working (employee report, 25 Sep 2026)."""
	from hrms.api.remote_checkin import session_open_until

	last = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["name", "time", "log_type", "shift", "shift_start", "shift_end", "shift_actual_end"],
		order_by="time desc",
		limit=1,
		ignore_permissions=True,
	)
	if not last or last[0].log_type != "IN":
		return None
	started = get_datetime(last[0].time)
	until = session_open_until(started, last[0].shift_actual_end)
	if now >= until:
		logger.info("[now] employee=%s open IN %s ended at %s — not a session", employee, started, until)
		return None
	hours = (now - started).total_seconds() / 3600
	first_in, leave = _leave_by(employee, last[0], started)
	return {
		"since": str(started),
		"hours": flt(hours, 2),
		"open_until": str(until),
		# The day's FIRST check-in and when the person may leave (owner, 28 Sep
		# 2026: late in, late out; early in, out as usual). Display only.
		"first_in": str(first_in) if first_in else None,
		"leave_by": str(leave) if leave else None,
	}


def _leave_by(employee, open_in, started):
	"""(the shift's first check-in, the time they may leave) for an open session.

	From the punch's OWN stamped shift window (shift_start / shift_end), the
	snapshot overtime prices the day by, and the FIRST IN of that shift: a
	check-out for lunch and back in must not move the leave time, just as it
	does not move where overtime begins (_pair_sessions: shift_first_in).
	(None, None) when the punch carries no window."""
	from hrms.utils.half_day_session import approved_session
	from hrms.utils.leave_by import leave_by

	if not (open_in.get("shift_start") and open_in.get("shift_end")):
		return None, None
	shift_start = get_datetime(open_in.shift_start)
	shift_end = get_datetime(open_in.shift_end)
	firsts = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"log_type": "IN",
			"shift": open_in.get("shift"),
			"shift_start": open_in.shift_start,
		},
		pluck="time",
		order_by="time asc",
		limit=1,
		ignore_permissions=True,
	)
	first_in = get_datetime(firsts[0]) if firsts else started
	session = approved_session(employee, shift_start.date())
	leave = leave_by(first_in, shift_start, shift_end, session=session)
	logger.info("[now] employee=%s first in %s -> leave by %s (%s)", employee, first_in, leave, session)
	return first_in, leave


def _shift_window(employee, on_date):
	"""Today's shift (assignment, else the default shift), as a window a person can read."""
	# hrms.utils.GEOFENCE, not shift_resolution — that module holds the punch
	# pairing rules (choose_shift, continues_session) and has no
	# resolve_assignment. Guessed wrong first and the bench said so
	# immediately: every caller ImportError'd.
	from hrms.utils.geofence import resolve_assignment

	try:
		assignment = resolve_assignment(employee, on_date)
	except Exception:
		# A shift that cannot be resolved must not take the top of Home with
		# it. The rest of the bar is still true.
		logger.exception("[now] could not resolve the shift for %s", employee)
		return None
	# No assignment covering today: the employee's default shift IS their shift,
	# as HRMS itself reads it (get_employee_shift, consider_default_shift=True).
	# Home said "No shift today" while Profile showed the default (owner, 24 Sep).
	shift_type = (assignment and assignment.shift_type) or default_shift_on(employee, on_date)
	if not shift_type:
		logger.info("[now] employee=%s has no assignment and no default shift", employee)
		return None
	start, end = frappe.db.get_value("Shift Type", shift_type, ["start_time", "end_time"]) or (
		None,
		None,
	)
	if not start or not end:
		return None
	return {
		"shift": shift_type,
		# Trimmed to HH:MM here rather than on the screen: a shift window is
		# read, not computed with, and "19:00:00" is three characters of noise
		# in a line that has to fit a phone.
		"start": _hhmm(start),
		"end": _hhmm(end),
	}


def default_shift_on(employee, on_date) -> str | None:
	"""The employee's default shift, on a working day. The one rule Home and the
	Calendar day sheet share for "no roster covers this day".

	A default shift does not make a rest day a workday: on a holiday or weekly
	off the answer is no shift, not "Not checked in · 09:00 to 18:00".
	"""
	if _is_rest_day(employee, on_date):
		return None
	return frappe.db.get_value("Employee", employee, "default_shift")


def _is_rest_day(employee, on_date) -> bool:
	"""On the employee's holiday list for `on_date` (holiday or weekly off)."""
	from erpnext.setup.doctype.employee.employee import is_holiday

	return bool(is_holiday(employee, on_date, raise_exception=False))


def _hhmm(value) -> str:
	"""HH:MM from whatever the field holds.

	NOT `str(value)[:5]`. A timedelta with a single-digit hour stringifies as
	"6:00:00", and slicing five characters off that gives "6:00:" — a trailing
	colon on the top line of Home. Found on the bench against a real night
	shift; the same 22:00 to 6:00 assignment that has already cost this app two
	separate defects.
	"""
	text = str(value)
	hours, _, rest = text.partition(":")
	minutes = rest.partition(":")[0]
	return f"{int(hours):02d}:{minutes[:2].zfill(2)}" if hours.isdigit() else text


def _last_completed(employee, now):
	"""The most recent OUT, when there is no session running.

	Read ONLY in that case: while somebody is checked in, when they last left
	is not what the top of Home should be saying.
	"""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "log_type": "OUT"},
		fields=["time"],
		order_by="time desc",
		limit=1,
		ignore_permissions=True,
	)
	if not rows:
		return None
	return str(rows[0].time)


def _state(session, shift, last_out, now):
	"""One word for what is true, and a sentence under it.

	FOUR STATES, and every employee is always in exactly one:

	  working    — a session is open. The number is the point.
	  done       — checked out today. Their day is finished and they can see it.
	  before     — on shift later today, not in yet.
	  off        — no shift today, nothing open. A rest day, and saying so is
	               better than an empty bar that reads as a broken screen.

	The `key` is for the screen to style and test against; the `label` is what
	renders, so the wording lives in one place rather than in every consumer.
	"""
	if session:
		return {"key": "working", "label": "Working"}

	if last_out and str(last_out)[:10] == str(now.date()):
		return {"key": "done", "label": "Done for today"}

	if shift:
		# A shift exists for today and nothing is open. Before its start time
		# that is "not in yet"; after, it is a day they have not punched — and
		# the honest word for both is the same, because the bar is not the
		# place to accuse somebody of missing a shift.
		return {"key": "before", "label": "Not checked in"}

	return {"key": "off", "label": "No shift today"}


@frappe.whitelist(methods=["GET", "POST"])
def get_now() -> dict:
	"""The one line at the top of Home."""
	from hrms.api import get_current_employee
	from hrms.utils.timezone import employee_now

	employee = get_current_employee()
	now = employee_now(employee)

	session = _open_session(employee, now)
	shift = _shift_window(employee, now.date())
	last_out = None if session else _last_completed(employee, now)

	payload = {
		"date": str(now.date()),
		# The employee's own wall clock, not the server's. A site in another
		# timezone put the wrong day at the top of Home near midnight.
		"time": now.strftime("%H:%M"),
		"shift": shift,
		"session": session,
		# The STATE WORD the plan asked for. Always present, because the bar's
		# whole job is to say what is true right now — and "nothing is true
		# right now" is not an outcome a status line is allowed to have.
		#
		# The first build made every part optional, so an employee with no
		# shift assigned and no open punch got an empty bar and Home opened on
		# "Last check-out was at 08:17 pm" exactly as before. Deployed 23 Sep
		# and it was the first thing the owner saw.
		"state": _state(session, shift, last_out, now),
		"last_out": last_out,
	}
	logger.info(
		"[now] employee=%s shift=%s open=%s",
		employee,
		bool(payload["shift"]),
		bool(payload["session"]),
	)
	return payload
