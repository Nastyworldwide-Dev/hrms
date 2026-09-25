"""Approved work after the shift is that shift day's overtime (owner, 25 Sep 2026).

"I finished my shift, went home, my boss asked me to carry on; I checked in
remotely and it was approved." Both punches of that session fall outside every
shift window, so they were filed off-shift, and off-shift never reaches
overtime (ot_calculation._is_eligible_checkin). Measured on the bench: the day
showed 1.0 h, the hour after 18:00, and not the 4 h worked from home.

An APPROVED session after the day's own shift ends now takes that shift's stamp
(the day it started, past midnight included, as night shifts already do).
The claim still has to be approved before anything is paid: this makes the
hours claimable, never paid. A punch inside the NEXT shift's window stays that
shift's arrival, so the two can never be double-counted.
"""

import logging
from datetime import timedelta

from frappe.utils import cint, get_datetime

logger = logging.getLogger(__name__)

#: A call-back belongs to the shift day it follows only while it is still the
#: evening/night of that day: past this the "day" it would join is gone.
MAX_AFTER_SHIFT = timedelta(hours=18)


def callback_stamp(punch, day_punch, next_window_start):
	"""The shift stamp an approved off-shift punch takes, or None. Pure.

	`day_punch` is the employee's latest shifted punch before this one (the
	day's own session); `next_window_start` the next shift occurrence's check-in
	window start after it, if any."""
	if not day_punch or not day_punch.get("shift") or not cint(punch.get("offshift")):
		return None
	when = get_datetime(punch["time"])
	day_end = get_datetime(day_punch.get("shift_actual_end") or day_punch.get("shift_end"))
	if not day_end or when <= day_end or when - day_end > MAX_AFTER_SHIFT:
		return None
	if next_window_start and when >= get_datetime(next_window_start):
		return None
	# Employee Checkin's own field names, so the stamp is written as it reads.
	return {
		"shift": day_punch["shift"],
		"shift_start": day_punch.get("shift_start"),
		"shift_end": day_punch.get("shift_end"),
		"shift_actual_start": day_punch.get("shift_actual_start"),
		# The day's own window end, as every punch of the day carries it: the OT
		# pricer measures from the shift's end and needs the session to name it
		# (bench: with None the whole 4 h call-back priced at nothing).
		"shift_actual_end": day_punch.get("shift_actual_end"),
		"overtime_type": day_punch.get("overtime_type"),
	}


def stamp_approved_callback(checkin_name):
	"""Give an approved off-shift punch its day's shift, and its session's other
	punch too. Returns the names stamped. Called on approval."""
	import frappe

	row = frappe.db.get_value(
		"Employee Checkin",
		checkin_name,
		["name", "employee", "time", "log_type", "shift", "offshift", "attendance"],
		as_dict=True,
	)
	if not row or row.attendance or not cint(row.offshift):
		return []
	day_punch = _day_punch_before(row.employee, row.time)
	stamp = callback_stamp(row, day_punch, _next_window_start(row.employee, day_punch))
	if not stamp:
		logger.info("[callback_session] %s at %s is not a call-back of a shift day", row.name, row.time)
		return []
	# the session: this punch and its partner (the OUT after an IN, the IN before an OUT)
	names = [row.name, *_partner(row)]
	for name in names:
		frappe.db.set_value(
			"Employee Checkin",
			name,
			{"offshift": 0, **stamp},
			update_modified=False,
		)
	logger.info("[callback_session] %s stamped onto %s %s", names, stamp["shift"], stamp["shift_start"])
	return names


def _day_punch_before(employee, when):
	import frappe

	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [get_datetime(when) - timedelta(hours=40), get_datetime(when)]],
			"shift": ["is", "set"],
			"offshift": 0,
			"skip_auto_attendance": 0,
		},
		fields=[
			"shift",
			"shift_start",
			"shift_end",
			"shift_actual_start",
			"shift_actual_end",
			"overtime_type",
			"time",
		],
		order_by="time desc",
		limit=1,
	)
	return rows[0] if rows else None


def _next_window_start(employee, day_punch):
	"""The check-in window start of the employee's NEXT shift occurrence after
	the day's shift. Asked at the day's shift end, the forward lookup answered
	with that same occurrence (bench: 08:00 the same morning), which read every
	evening punch as "inside the next shift"; so ask from just after its window
	closes."""
	if not day_punch or not (day_punch.get("shift_actual_end") or day_punch.get("shift_end")):
		return None
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift

	after = get_datetime(day_punch.get("shift_actual_end") or day_punch["shift_end"]) + timedelta(minutes=1)
	nxt = get_employee_shift(employee, after, True, "forward")
	start = get_datetime(nxt.get("actual_start")) if nxt and nxt.get("actual_start") else None
	return start if start and start > after else None


def _partner(row):
	"""The other punch of an off-shift IN/OUT pair, when it is off-shift too."""
	import frappe

	after = row.log_type == "IN"
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": row.employee,
			"time": [">" if after else "<", row.time],
			"offshift": 1,
			"attendance": ["is", "not set"],
		},
		fields=["name", "log_type", "remote_approval_status"],
		order_by="time asc" if after else "time desc",
		limit=1,
	)
	want = "OUT" if after else "IN"
	if rows and rows[0].log_type == want and rows[0].remote_approval_status != "Rejected":
		return [rows[0].name]
	return []
