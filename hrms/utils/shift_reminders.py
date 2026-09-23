"""Check-in / check-out reminders, sent to the person only.

Owner ruling, 23 Sep 2026:
- 15 min after the shift starts, a person who has not checked in for that
  shift is told "You haven't checked in yet. Tap to check in."
- 30 min after the shift ends, a person whose last punch of that shift is IN
  is told "You're still checked in. Tap to check out."
- Only people with a shift that day (Active submitted Shift Assignment covering
  the day, else Employee.default_shift), never on a rest day or holiday.
- No manager copy. Staff can turn it off on the You page (ON by default).

Runs every 5 minutes (hooks.py cron). Each reminder has a 5-minute due window
on the EMPLOYEE's clock so one tick fires it; a PWA Notification with the same
to_user + message created since that SHIFT started also stops it (a late or
doubled tick) — keyed to the shift, so a night shift's morning check-out
reminder is neither skipped nor doubled by the server's calendar day.

Delivery is a PWA Notification row: its after_insert queues the push. No
reference doctype, so the push and the feed open /hrms (home, where the
check-in button is).
"""

from __future__ import annotations

import datetime
import logging

import frappe
from frappe.utils import add_days, get_datetime, getdate, now_datetime

logger = logging.getLogger(__name__)

#: Employee Check field; 1 = send reminders (default).
FIELD = "nadi_shift_reminders"

CHECK_IN_MESSAGE = "You haven't checked in yet. Tap to check in."
CHECK_OUT_MESSAGE = "You're still checked in. Tap to check out."

CHECK_IN_AFTER = datetime.timedelta(minutes=15)
CHECK_OUT_AFTER = datetime.timedelta(minutes=30)
#: one cron tick wide: the reminder fires on exactly one tick
WINDOW = datetime.timedelta(minutes=5)
#: a punch this long before the shift start still belongs to the shift when
#: the Shift Type does not say otherwise (the Shift Type default is 60)
DEFAULT_EARLY_MINUTES = 60
DEFAULT_LATE_MINUTES = 60


def send_due_reminders() -> int:
	"""Scheduler entry point. Returns how many reminders were created."""
	people = frappe.get_all(
		"Employee",
		filters={"status": "Active", "user_id": ["is", "set"], FIELD: 1},
		fields=["name", "user_id", "default_shift"],
	)
	if not people:
		logger.info("[shift_reminders] nobody opted in with a user; nothing to do")
		return 0

	system_today = getdate(now_datetime())
	assignments = _assignments_by_employee(system_today)
	candidates = []
	shift_types = {}
	for person in people:
		now = _employee_now(person.name)
		for day in (getdate(add_days(now.date(), -1)), now.date()):
			shift = _shift_for(person, day, assignments)
			if not shift:
				continue
			if shift not in shift_types:
				shift_types[shift] = _shift_type(shift)
			times = shift_types[shift]
			if not times:
				continue
			start, end = shift_bounds(day, times.start_time, times.end_time)
			kind = due_kind(now, start, end)
			if kind:
				candidates.append(
					frappe._dict(
						employee=person.name,
						user=person.user_id,
						shift=shift,
						day=day,
						start=start,
						end=end,
						now=now,
						kind=kind,
						early=datetime.timedelta(
							minutes=_minutes(
								times.get("begin_check_in_before_shift_start_time"), DEFAULT_EARLY_MINUTES
							)
						),
						late=datetime.timedelta(
							minutes=_minutes(
								times.get("allow_check_out_after_shift_end_time"), DEFAULT_LATE_MINUTES
							)
						),
					)
				)

	candidates = [c for c in candidates if _is_working_day(c)]
	if not candidates:
		logger.info("[shift_reminders] %d people checked, no reminder due", len(people))
		return 0

	punches = _punches_for(candidates)
	already = _sent_this_shift(candidates)
	sent = 0
	for c in candidates:
		message = CHECK_IN_MESSAGE if c.kind == "in" else CHECK_OUT_MESSAGE
		if any(at >= c.start for at in already.get((c.user, message), [])):
			continue
		own = [p for p in punches.get(c.employee, []) if _belongs(p, c)]
		if c.kind == "in" and any(p.log_type == "IN" for p in own):
			continue
		if c.kind == "out" and not (own and own[-1].log_type == "IN"):
			continue
		# One person's failure must not sink the rest: an unhandled error rolled
		# back the whole tick, and the 5-minute window means nobody is retried.
		# Each reminder is committed on its own (review of 50403096f).
		try:
			_notify(c.user, message)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			logger.exception("[shift_reminders] could not remind %s (%s); skipped", c.employee, c.kind)
			continue
		already.setdefault((c.user, message), []).append(c.start)
		sent += 1
	logger.info(
		"[shift_reminders] %d people, %d due, %d reminder(s) sent", len(people), len(candidates), sent
	)
	return sent


def shift_bounds(day, start_time, end_time):
	"""Start and end datetimes of the shift that starts on `day`.

	A night shift (end at or before start) ends the next day.
	"""
	start = datetime.datetime.combine(getdate(day), _as_time(start_time))
	end = datetime.datetime.combine(getdate(day), _as_time(end_time))
	if end <= start:
		end += datetime.timedelta(days=1)
	return start, end


def due_kind(now, start, end):
	"""'in', 'out' or None: which reminder's 5-minute window `now` is in."""
	if start + CHECK_IN_AFTER <= now < start + CHECK_IN_AFTER + WINDOW:
		return "in"
	if end + CHECK_OUT_AFTER <= now < end + CHECK_OUT_AFTER + WINDOW:
		return "out"
	return None


@frappe.whitelist()
def get_shift_reminders() -> bool:
	"""Whether the session user's own reminders are on."""
	from hrms.utils.identity import require_employee

	employee = require_employee()
	value = frappe.db.get_value("Employee", employee, FIELD)
	# a site where the patch has not run yet reads None: the default is ON
	return value is None or bool(int(value))


@frappe.whitelist(methods=["POST"])
def set_shift_reminders(enabled) -> bool:
	"""Turn the session user's own reminders on or off. Own employee only."""
	from hrms.utils.identity import require_employee

	employee = require_employee()
	on = str(enabled).lower() in ("1", "true", "yes", "on")
	# set_value, not doc.save: staff may not hold write on their Employee record,
	# and this is the one field they own. The employee is the session's own.
	frappe.db.set_value("Employee", employee, FIELD, 1 if on else 0)
	logger.info("[shift_reminders] %s turned reminders %s", employee, "on" if on else "off")
	return on


def _employee_now(employee):
	from hrms.utils.timezone import employee_now

	return employee_now(employee)


def _is_working_day(c) -> bool:
	"""A rest day or holiday gets no reminder."""
	from hrms.utils.ot_calculation import _classify_day

	try:
		kind = _classify_day(c.employee, c.day, "normal", shift=c.shift)
	except Exception:
		logger.exception("[shift_reminders] could not classify %s for %s; skipped", c.day, c.employee)
		return False
	if kind != "normal":
		logger.info("[shift_reminders] %s is a %s for %s; no reminder", c.day, kind, c.employee)
		return False
	return True


def _assignments_by_employee(system_today):
	"""Active submitted assignments touching yesterday..tomorrow, per employee.

	One query for everyone; the covering one per day is picked in Python.
	"""
	rows = frappe.get_all(
		"Shift Assignment",
		filters={"status": "Active", "docstatus": 1, "start_date": ["<=", add_days(system_today, 1)]},
		or_filters=[["end_date", ">=", add_days(system_today, -2)], ["end_date", "is", "not set"]],
		fields=["employee", "shift_type", "start_date", "end_date"],
		order_by="start_date desc",
	)
	out = {}
	for row in rows:
		out.setdefault(row.employee, []).append(row)
	logger.info("[shift_reminders] %d active assignment(s) around %s", len(rows), system_today)
	return out


def _shift_for(person, day, assignments):
	day = getdate(day)
	for row in assignments.get(person.name, []):
		if getdate(row.start_date) <= day and (not row.end_date or getdate(row.end_date) >= day):
			return row.shift_type
	return person.default_shift or None


def _shift_type(name):
	return frappe.db.get_value(
		"Shift Type",
		name,
		[
			"start_time",
			"end_time",
			"begin_check_in_before_shift_start_time",
			"allow_check_out_after_shift_end_time",
		],
		as_dict=True,
	)


def _punches_for(candidates):
	"""One query: every due employee's punches from the earliest window on."""
	since = min(c.start - c.early for c in candidates)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ["in", sorted({c.employee for c in candidates})],
			"time": [">=", since],
		},
		fields=["employee", "time", "log_type", "shift_start"],
		order_by="time asc",
	)
	out = {}
	for row in rows:
		out.setdefault(row.employee, []).append(row)
	logger.info("[shift_reminders] %d punch(es) for %d due reminder(s)", len(rows), len(candidates))
	return out


def _belongs(punch, c) -> bool:
	"""The punch is this shift's: stamped with its start, or inside its window."""
	if punch.shift_start and get_datetime(punch.shift_start) == c.start:
		return True
	return c.start - c.early <= get_datetime(punch.time) <= c.end + c.late


def _sent_this_shift(candidates):
	"""{(user, message): [sent times]} since the earliest shift start in play.

	Keyed to the SHIFT, not the calendar day: a night shift's check-out
	reminder lands the next morning, and a day-keyed check skipped or doubled
	it depending on the server's clock. A reminder counts as sent for a shift
	when it was created at or after that shift's start.
	"""
	since = min(c.start for c in candidates) - datetime.timedelta(hours=1)
	rows = frappe.get_all(
		"PWA Notification",
		filters={
			"to_user": ["in", sorted({c.user for c in candidates})],
			"message": ["in", [CHECK_IN_MESSAGE, CHECK_OUT_MESSAGE]],
			"creation": [">=", since],
		},
		fields=["to_user", "message", "creation"],
	)
	sent = {}
	for row in rows:
		sent.setdefault((row.to_user, row.message), []).append(get_datetime(row.creation))
	logger.debug("[shift_reminders] %d reminder(s) already sent since %s", len(rows), since)
	return sent


def _notify(user, message):
	frappe.get_doc(
		{
			"doctype": "PWA Notification",
			"to_user": user,
			"from_user": "Administrator",
			"message": message,
			"read": 0,
		}
	).insert(ignore_permissions=True)
	logger.info("[shift_reminders] reminded %s: %s", user, message)


def _as_time(value):
	if isinstance(value, datetime.time):
		return value
	if isinstance(value, datetime.timedelta):
		return (datetime.datetime.min + value).time()
	parts = [int(float(p)) for p in str(value).split(":")]
	while len(parts) < 3:
		parts.append(0)
	return datetime.time(parts[0], parts[1], parts[2])


def _minutes(value, default):
	try:
		return int(value) if value not in (None, "") else default
	except (TypeError, ValueError):
		return default
