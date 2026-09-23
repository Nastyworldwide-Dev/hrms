# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""What is happening on each date (PWA Calendar, revamp §4).

The owner's ask was "each date must serve function — what is going on in that
date?" — without the screen overflowing with text. The answer is structural
rather than editorial, and it is the whole design of this module:

    THE MONTH GRID CARRIES DOTS. THE DAY SHEET CARRIES WORDS.

A tile is about 44px. It can hold a number and up to three 4px dots and
nothing else; trying to fit a sentence into it is what makes a calendar
unreadable. So this endpoint returns, per date, the small set of FLAGS a tile
can draw — and `calendar.day` (slice C3) returns the sentences.

That is progressive disclosure (NN/g) applied literally: the overview shows
what KIND of day it is, and one tap shows what actually happened.

Session-scoped by construction: no endpoint takes an employee.
"""

import logging
from datetime import timedelta

import frappe
from frappe.utils import add_days, date_diff, flt, getdate

from hrms.utils.timezone import employee_now
from hrms.utils.worked_days import punch_days

logger = logging.getLogger(__name__)

#: How many dots a tile can hold before it stops being legible. Three is not a
#: design preference — it is what fits beside a two-digit date at 44px with a
#: 4pt gap, which is the tap-target floor the tile cannot go under.
MAX_DOTS = 3

#: The flags, in the order they are drawn. Order is fixed so a person learns
#: the position rather than re-reading the legend: the first dot is always
#: "you were off", never sometimes something else.
#: Travel and training sit beside leave (owner ruling R1, 23 Sep 2026): all
#: three say "you were away from your usual work". "open" (a request waiting
#: on the caller as approver) sits before needs_you.
FLAG_ORDER = ("leave", "travel", "training", "holiday", "event", "open", "needs_you")

#: The date fields of each request type an approver decides, for the "open"
#: dot. Dates ONLY — never a reason (owner: managers see the type, never why).
#: A type not listed here (Expense Claim, Replacement Leave Claim) has no day.
OPEN_DATE_FIELDS = {
	"Leave Application": ("from_date", "to_date"),
	"OT Request": ("ot_date",),
	"Attendance Request": ("from_date", "to_date"),
	"Shift Request": ("from_date", "to_date"),
	"Compensatory Leave Request": ("work_from_date", "work_end_date"),
}

#: How far a month request may reach. A calendar shows a month; a caller
#: asking for two years is either a bug or a scrape, and either way it is a
#: table scan per employee.
MAX_SPAN_DAYS = 62


def _window(from_date: str, to_date: str):
	start, end = getdate(from_date), getdate(to_date)
	if date_diff(end, start) < 0:
		frappe.throw(frappe._("The calendar's end date is before its start date."))
	if date_diff(end, start) > MAX_SPAN_DAYS:
		frappe.throw(frappe._("A calendar request covers at most {0} days.").format(MAX_SPAN_DAYS))
	return start, end


def _leave_days(employee: str, start, end) -> set:
	"""Days the employee is on approved leave.

	Submitted only. A leave application still waiting on an approver is not a
	day off — marking it as one on the grid is how somebody books a flight
	against leave that is later rejected.
	"""
	days = set()
	for row in frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ("<=", end),
			"to_date": (">=", start),
		},
		fields=["from_date", "to_date"],
		ignore_permissions=True,
	):
		day = max(getdate(row.from_date), start)
		last = min(getdate(row.to_date), end)
		while date_diff(last, day) >= 0:
			days.add(day)
			day = add_days(day, 1)
	return days


def _span(first, last, start, end) -> set:
	"""Every date from `first` to `last`, clipped to the window."""
	day = max(getdate(first), start)
	last = min(getdate(last or first), end)
	days = set()
	while day <= last:
		days.add(day)
		day += timedelta(days=1)
	logger.debug("[calendar] span %s..%s -> %d days", first, last, len(days))
	return days


def _travel_days(employee: str, start, end) -> set:
	"""Days of the employee's approved trips (submitted Travel Requests).

	A trip runs from its first leg's departure to its last leg's arrival; the
	days between are travel too. On Duty attendance requests are NOT travel:
	they carry no signal that the duty was away.
	"""
	if not frappe.db.exists("DocType", "Travel Request"):
		return set()
	# ceiling: reads every approved trip of the employee, upgrade: filter legs
	# by date if one person ever holds hundreds of Travel Requests.
	names = [
		row.name
		for row in frappe.get_all(
			"Travel Request",
			filters={"employee": employee, "docstatus": 1},
			fields=["name"],
			ignore_permissions=True,
		)
	]
	if not names:
		return set()
	legs = {}
	for row in frappe.get_all(
		"Travel Itinerary",
		filters={"parenttype": "Travel Request", "parent": ("in", names)},
		fields=["parent", "departure_date", "arrival_date"],
		ignore_permissions=True,
	):
		for value in (row.departure_date, row.arrival_date):
			if value:
				legs.setdefault(row.parent, []).append(getdate(value))
	days = set()
	for dates in legs.values():
		days |= _span(min(dates), max(dates), start, end)
	logger.info("[calendar] travel employee=%s trips=%d days=%d", employee, len(legs), len(days))
	return days


def _training_days(employee: str, start, end) -> set:
	"""Days of Training Events the employee is listed on, unless cancelled."""
	if not frappe.db.exists("DocType", "Training Event"):
		return set()
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
		return set()
	days = set()
	for row in frappe.get_all(
		"Training Event",
		filters={
			"name": ("in", events),
			"docstatus": 1,
			"event_status": ("!=", "Cancelled"),
			"start_time": ("<=", f"{end} 23:59:59"),
			"end_time": (">=", f"{start} 00:00:00"),
		},
		fields=["start_time", "end_time"],
		ignore_permissions=True,
	):
		if row.start_time:
			days |= _span(row.start_time, row.end_time, start, end)
	logger.info("[calendar] training employee=%s events=%d days=%d", employee, len(events), len(days))
	return days


def _open_days(start, end) -> set:
	"""Days covered by requests waiting on the CALLER's decision.

	Reuses the Approvals page's own list, so a dot can never admit a request
	the caller could not already open there; only its "yours" section counts.
	Reads dates only — a manager sees the type of a request, never its reason.
	"""
	from hrms.api.approvals_list import YOURS, get_waiting_for_me
	from hrms.api.team import is_approver

	days, rows = set(), []
	try:
		if not is_approver():
			return set()
		rows = get_waiting_for_me()["rows"]
		for row in rows:
			fields = OPEN_DATE_FIELDS.get(row.get("doctype"))
			if row.get("section") != YOURS or not fields:
				continue
			# A list of fields, so the answer is always a tuple: (first, last)
			# or (the one date,).
			dates = frappe.db.get_value(row["doctype"], row["name"], list(fields)) or ()
			if dates and dates[0]:
				days |= _span(dates[0], dates[-1], start, end)
	except Exception:
		# The least of the dots: a broken queue must not take the month down.
		logger.exception("[calendar] approvals queue unavailable; no open dots")
		return set()
	logger.info("[calendar] open user=%s rows=%d days=%d", frappe.session.user, len(rows), len(days))
	return days


def _holidays(employee: str, start, end) -> set:
	from hrms.api import get_holidays_for_calendar

	return {getdate(value) for value in get_holidays_for_calendar(employee, start, end)}


def _board_missing(error: Exception) -> bool:
	"""The board is not there: its doctype is unknown, or its table is.

	Only these are swallowed by _event_days; anything else is a bug and must
	be loud (review of 8fc7dbe6a). By name for the DB error, so this reads no
	`frappe.db` at import, when there is no connection yet.
	"""
	return isinstance(error, frappe.DoesNotExistError) or type(error).__name__ in (
		"ProgrammingError",
		"TableMissingError",
	)


def _event_days(employee: str, start, end) -> set:
	"""Company events dated inside the window — today, announcements.

	Reuses the announcement board's own fence rather than re-deriving who sees
	what: an Event dot on a day the reader may not see the announcement for
	would tell them something is happening and refuse to say what.
	"""
	from hrms.api.announcements import _reader, _visible_rows

	reader = _reader()
	if not reader:
		return set()
	try:
		rows = _visible_rows(reader)
	except Exception as error:
		if not _board_missing(error):
			raise
		# Narrowed to "the board is not there" (review of 8fc7dbe6a): a real
		# bug in the board must still fail loudly.
		# The least of four dot kinds. A site without the announcement board
		# (seen on fresh.local, 23 Sep) made the whole month a 403, so every
		# employee lost their leave, holiday and needs-you dots too.
		logger.exception("[calendar] announcements unavailable; no event dots")
		return set()
	days = set()
	for row in rows:
		if row.get("category") != "Event":
			continue
		day = getdate(row.get("publish_from"))
		if start <= day <= end:
			days.add(day)
	return days


def _needs_you_days(employee: str, start, end, worked: dict, marked: set) -> set:
	"""Days with something for the EMPLOYEE to do about their own record.

	Three shapes, all of them things that cost money if they are left:
	  * a day they worked with no attendance row at all;
	  * a day with overtime hours and no claim filed;
	  * an attendance row still waiting on somebody.

	Not "a day with a problem HR should look at" — this dot is on the
	employee's own calendar and every one of them is an action they can take.
	"""
	# Never today or later, on the employee's own clock (owner bug, 23 Sep):
	# today's attendance is written later by auto-attendance, so a day still
	# being worked is not a day with a missing row.
	today = employee_now(employee).date()
	days = {day for day in worked if day not in marked and day < today}

	# OT Request ONLY. Replacement Leave Claim has no per-day date at all — it
	# is banked against a MONTH (`bank_month`) and its `claimed_days` is a
	# count, so there is no day to mark as claimed. The first version of this
	# queried a `work_date` field that does not exist, inside a try/except that
	# would have swallowed the error forever and quietly marked every OT day as
	# unclaimed. Checked against the doctype rather than assumed.
	claimed = {
		getdate(value)
		for value in frappe.get_all(
			"OT Request",
			filters={
				"employee": employee,
				"docstatus": ("<", 2),
				"ot_date": ("between", [start, end]),
			},
			pluck="ot_date",
			ignore_permissions=True,
		)
		if value
	}

	for row in frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ("between", [start, end]),
			"docstatus": ("<", 2),
		},
		fields=["attendance_date", "ot_hours"],
		ignore_permissions=True,
	):
		day = getdate(row.attendance_date)
		if flt(row.ot_hours) > 0 and day not in claimed:
			days.add(day)

	return days


@frappe.whitelist(methods=["GET", "POST"])
def get_month_flags(from_date: str, to_date: str) -> dict:
	"""Per date, the flags a tile can draw. No words, by design.

	Returns `{ "2026-09-04": ["leave"], ... }` — dates with no flags are
	ABSENT rather than present with an empty list, because a month of empty
	arrays is a payload that says nothing in thirty lines.
	"""
	from hrms.api import get_current_employee

	employee = get_current_employee()
	start, end = _window(from_date, to_date)

	marked = {
		getdate(value)
		for value in frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"attendance_date": ("between", [start, end]),
				"docstatus": ("<", 2),
			},
			pluck="attendance_date",
			ignore_permissions=True,
		)
	}
	worked = {}
	for value in frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ("between", [f"{start} 00:00:00", f"{end} 23:59:59"]),
		},
		pluck="shift_actual_start",
		ignore_permissions=True,
	):
		if value:
			worked[getdate(value)] = True

	# ONE rule for "worked" (hrms/utils/worked_days.py): an IN followed by an
	# OUT is a worked day even before auto-attendance writes its row, and
	# today with an open IN is "in progress". The grid fills them; the
	# attendance calendar alone left a finished day blank until the job ran.
	paired, open_days = punch_days(employee, start, end)
	today = employee_now(employee).date()

	buckets = {
		"leave": _leave_days(employee, start, end),
		"travel": _travel_days(employee, start, end),
		"training": _training_days(employee, start, end),
		"holiday": _holidays(employee, start, end),
		"event": _event_days(employee, start, end),
		"open": _open_days(start, end),
		"needs_you": _needs_you_days(employee, start, end, worked, marked),
	}

	flags = {}
	for name in FLAG_ORDER:
		for day in buckets[name]:
			if not (start <= day <= end):
				continue
			entry = flags.setdefault(str(day), [])
			# The cap is applied HERE rather than on the screen, so the payload
			# and the tile always agree about what is drawn. FLAG_ORDER decides
			# which survives, and it is fixed so a person learns the position.
			if len(entry) < MAX_DOTS:
				entry.append(name)

	logger.info(
		"[calendar] flags employee=%s %s..%s days=%d paired=%d open_today=%s",
		employee,
		start,
		end,
		len(flags),
		len(paired),
		today in open_days,
	)
	return {
		"flags": flags,
		"legend": list(FLAG_ORDER),
		"paired": sorted(str(day) for day in paired if start <= day <= end),
		"open_today": str(today) if today in open_days and start <= today <= end else None,
	}


# ---------------------------------------------------------------------------
# THE DAY SHEET (slice C3) — where the words live.
#
# The grid answers "what kind of day was that". This answers "what actually
# happened", and it is the only place on the calendar that renders sentences.
#
# PERSONA IS THE SERVER'S ANSWER, NOT THE SCREEN'S (revamp P5/KR2). The sheet
# returns only the sections the caller is entitled to, so the PWA renders what
# arrives and holds no role logic at all. An employee gets their own day; an
# approver additionally gets who in their reporting line is off; a manager
# gets the coverage line. Nobody can enumerate a department by tampering with
# a request, because the list of people is derived from the caller's identity
# rather than from anything they send.
#
# LEAVE TYPE YES, LEAVE REASON NEVER (owner's ruling Q3, 22 Sep 2026). A
# manager may see WHO is off and what kind of leave it is. Why somebody is off
# is between them, their approver and HR.


def _my_punches(employee: str, day) -> list[dict]:
	"""The taps themselves, in order, as a timeline.

	The raw record rather than a computed total: an employee checking a day is
	usually checking whether a specific tap registered, and a single "8h 03m"
	cannot answer that.
	"""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]),
		},
		fields=["name", "time", "log_type", "skip_auto_attendance"],
		order_by="time asc",
		ignore_permissions=True,
	)
	return [
		{
			"time": str(row.time),
			"log_type": row.log_type,
			# A skipped punch is shown, never hidden: "my tap is missing" and
			# "my tap was set aside" are different problems with different
			# answers, and hiding the second makes it look like the first.
			"skipped": bool(row.skip_auto_attendance),
		}
		for row in rows
	]


def _day_shift(employee: str, day, attendance) -> str | None:
	"""The shift the day was actually worked on (owner, 23 Sep: "No shift" on
	a worked day). The day's attendance first, then its check-ins, then the
	roster; the roster alone missed every day worked off-roster."""
	if attendance and attendance.get("shift"):
		return attendance.shift
	checkin_shift = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			# By the shift's own start date, not the punch time: a night
			# shift's 06:00 check-out belongs to the night before.
			"shift_start": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]),
			"shift": ("is", "set"),
		},
		pluck="shift",
		order_by="shift_start asc",
		limit=1,
		ignore_permissions=True,
	)
	if checkin_shift:
		return checkin_shift[0]
	# The roster: an assignment that covers the day (an ended one no longer does).
	for row in frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "start_date": ("<=", day), "docstatus": 1, "status": "Active"},
		fields=["shift_type", "end_date"],
		order_by="start_date desc",
		limit=5,
		ignore_permissions=True,
	):
		if not row.end_date or getdate(row.end_date) >= day:
			return row.shift_type
	return None


def _my_day(employee: str, day) -> dict:
	"""Everything about the caller's own day."""
	attendance = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": day, "docstatus": ("<", 2)},
		["name", "status", "working_hours", "ot_hours", "shift", "leave_type"],
		as_dict=True,
	)
	shift = _day_shift(employee, day, attendance)
	window = None
	if shift:
		start, end = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"]) or (None, None)
		if start and end:
			window = {"shift": shift, "start": str(start), "end": str(end)}

	return {
		"date": str(day),
		"status": attendance.status if attendance else None,
		"leave_type": attendance.leave_type if attendance else None,
		"worked_hours": flt(attendance.working_hours) if attendance else 0.0,
		"ot_hours": flt(attendance.ot_hours) if attendance else 0.0,
		"shift": window,
		"punches": _my_punches(employee, day),
		"claim": _day_claim(employee, day),
	}


#: A live claim outranks a refused one: a rejected request followed by a new
#: one is waiting, not rejected.
_CLAIM_RANK = {"Open": 0, "Approved": 0, "Rejected": 1}


def _day_claim(employee: str, day) -> dict | None:
	"""The caller's own overtime claim for the day, so the sheet stops offering
	"Claim" on a day already claimed (01-calendar.md §4 rows 3-5). The
	employee comes from the session, never the request."""
	claims = frappe.get_all(
		"OT Request",
		filters={"employee": employee, "ot_date": day, "docstatus": ("<", 2)},
		fields=["name", "status"],
		order_by="creation desc",
		ignore_permissions=True,
	)
	if not claims:
		return None
	claim = min(claims, key=lambda row: _CLAIM_RANK.get(row.status, 2))
	# The first designated approver — the order OT notifications try
	# (pwa_notifications._get_ot_approver). Blank when none: the sheet then
	# says "your approver" rather than guess a name.
	from hrms.hr.utils import get_designated_approvers

	name = ""
	for approver in get_designated_approvers(employee, "leave_approver", "leave_approvers"):
		# A disabled account never receives the claim; name the next one.
		if not frappe.db.get_value("User", approver, "enabled"):
			continue
		name = frappe.db.get_value("User", approver, "full_name") or ""
		if name:
			break
	logger.info("[calendar] day %s claim %s (%s)", day, claim.name, claim.status)
	return {"status": claim.status, "approver_name": name}


def _who_is_off(employees: list[str], day) -> list[dict]:
	"""Names and leave TYPE for a given set of people on a given day.

	The caller has already been established as entitled to these specific
	employees; this function takes the list rather than deriving it, so there
	is exactly one place that decides who may be looked at.
	"""
	if not employees:
		return []
	rows = frappe.get_all(
		"Leave Application",
		filters={
			"employee": ("in", employees),
			"docstatus": 1,
			"status": "Approved",
			"from_date": ("<=", day),
			"to_date": (">=", day),
		},
		fields=["employee", "employee_name", "leave_type", "half_day"],
		ignore_permissions=True,
	)
	return [
		{
			"employee": row.employee,
			"name": row.employee_name,
			"leave_type": row.leave_type,
			"half_day": bool(row.half_day),
			# `description` is deliberately NOT read. Owner's ruling: a manager
			# sees who is off and what kind of leave; why is not theirs.
		}
		for row in rows
	]


def _coverage(employees: list[str], day) -> dict:
	"""The number a manager opens a calendar for: how many of my people are in.

	Counted from the same list `_who_is_off` uses, so the line and the names
	beneath it can never disagree about the same day.
	"""
	if not employees:
		return {}
	marked = frappe.get_all(
		"Attendance",
		filters={
			"employee": ("in", employees),
			"attendance_date": day,
			"docstatus": ("<", 2),
		},
		fields=["employee", "status"],
		ignore_permissions=True,
	)
	by_status = {}
	for row in marked:
		by_status[row.status] = by_status.get(row.status, 0) + 1
	seen = {row.employee for row in marked}
	return {
		"headcount": len(employees),
		"present": by_status.get("Present", 0) + by_status.get("Half Day", 0),
		"on_leave": by_status.get("On Leave", 0),
		"absent": by_status.get("Absent", 0),
		# Nobody has said anything about these people for this day. On a past
		# day that is the number that costs money.
		"unmarked": len(employees) - len(seen),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_day(date: str) -> dict:
	"""One day, with only the sections the caller is entitled to.

	The PWA renders whatever arrives. It holds no role logic, so there is
	nothing on that side to get wrong and nothing to keep in step with this.
	"""
	from hrms.api import get_current_employee
	from hrms.hr.utils import get_direct_report_employees

	if not isinstance(date, str) or not date.strip():
		frappe.throw(frappe._("A day must be named."), frappe.PermissionError)
	day = getdate(date.strip())

	employee = get_current_employee()
	sections = {"me": _my_day(employee, day)}

	# The caller's DIRECT team (owner ruling 1, 23 Sep 2026): the same people
	# the Team page lists, not everyone routed to them for approval. Derived
	# from identity, never from anything sent. An empty list means NO
	# ADMISSION rather than no filter.
	try:
		team = [name for name in get_direct_report_employees(frappe.session.user) if name != employee]
	except Exception:
		logger.exception("[calendar] could not resolve the caller's team")
		team = []

	if team:
		sections["team_off"] = _who_is_off(team, day)
		sections["coverage"] = _coverage(team, day)

	logger.info(
		"[calendar] day employee=%s date=%s sections=%s team=%d",
		employee,
		day,
		sorted(sections),
		len(team),
	)
	return sections
