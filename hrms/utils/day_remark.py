"""One re-mark for every event that changes a past employee-day's evidence.

    remark_day_after_commit(employee, day, reason) -> bool

After the caller's transaction commits, one deduplicated background job per
employee-day re-marks that day through the engine
(`attendance_recovery._remark_released_day`: every punch of the shift day,
linked or not, through `ShiftType.mark_attendance_for_shift_logs`), so the
Attendance row, the Shift Attendance report and OT read the new evidence at
once instead of at the next hourly run — or never, for a day whose punches are
all linked already (a rejection after the day was marked).

Protections are the recovery's own (`attendance_recovery._day_protection`):
today, HR-edited, HR-removed, leave, attendance request, paid / approved OT.
A protected day is not touched; the Unclaimable Days detectors list it for HR.
A shift still running is left to the hourly job.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from functools import partial

import frappe
from frappe.utils import getdate

from hrms.hr.doctype.shift_type.shift_type import lock_employee_row
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

JOB_METHOD = "hrms.utils.day_remark.remark_day"


def remark_day_after_commit(employee, day, reason) -> bool:
	"""Queue the engine's re-mark of `employee` on `day` for after commit. False when
	there is nothing to queue: no employee or day, or the day is today or later."""
	if not employee or not day:
		return False
	day = getdate(day)
	if day >= employee_now(employee).date():
		logger.info("[day_remark] %s on %s (%s) is today: left to the hourly job", employee, day, reason)
		return False
	frappe.db.after_commit.add(partial(_enqueue, employee, str(day), reason))
	logger.info("[day_remark] %s on %s queued after commit: %s", employee, day, reason)
	return True


def _enqueue(employee, day, reason):
	# ceiling: a job already RUNNING for the day drops this one (deduplicate), upgrade:
	# re-queue from the job's end if a change lands mid-run; the hourly/nightly read it meanwhile
	frappe.enqueue(
		JOB_METHOD,
		queue="short",
		job_id=f"day-remark::{employee}::{day}",
		deduplicate=True,
		employee=employee,
		day=day,
		reason=reason,
	)


def punch_day(checkin):
	"""(employee, shift day) of an Employee Checkin, or (None, None) when it is gone."""
	row = frappe.db.get_value("Employee Checkin", checkin, ["employee", "shift_start", "time"], as_dict=True)
	if not row:
		return None, None
	return row.employee, getdate(row.shift_start or row.time)


def remark_day(employee, day, reason=""):
	"""The job: re-mark one past employee-day through the engine, unless it is protected."""
	from hrms.hr.doctype.shift_type import shift_type
	from hrms.utils import attendance_recovery as rec

	day = getdate(day)
	if _shift_still_running(employee, day):
		logger.info("[day_remark] %s on %s: shift still running, left to the hourly job", employee, day)
		return {"action": "running"}
	lock_employee_row(employee)
	held = rec._day_protection(employee, day, for_update=True)
	if held:
		logger.info("[day_remark] %s on %s held (%s): %s", employee, day, reason, held)
		return {"action": "held", "detail": held}
	result = rec._remark_released_day(employee, day, apply=True)
	retired = _retire_unmarkable_rows(employee, day, result, shift_type)
	logger.info(
		"[day_remark] %s on %s re-marked (%s): marked=%s retired=%s errors=%s",
		employee,
		day,
		reason,
		result.get("marked"),
		retired,
		result.get("errors"),
	)
	return {"action": "remarked", "retired": retired, **result}


def _shift_still_running(employee, day) -> bool:
	start = datetime.combine(day, time.min)
	return bool(
		frappe.db.exists(
			"Employee Checkin",
			[
				["employee", "=", employee],
				["shift_start", ">=", start],
				["shift_start", "<", start + timedelta(days=1)],
				["shift_actual_end", ">", employee_now(employee)],
			],
		)
	)


def _retire_unmarkable_rows(employee, day, result, shift_type) -> list:
	"""A punch-owned row the engine would no longer write (every punch of its shift
	rejected or skipped, or a rest day left without an approved pair) is cancelled,
	so the day reads what the engine marks from scratch. HR's, leave and mirrored
	rows are never found (get_automation_attendance); protected days never get here."""
	marking = {e.get("shift") for e in result.get("expected") or [] if e.get("status")}
	shifts = {
		s
		for s in frappe.get_all(
			"Employee Checkin",
			filters=[
				["employee", "=", employee],
				["shift_start", ">=", datetime.combine(day, time.min)],
				["shift_start", "<", datetime.combine(day, time.min) + timedelta(days=1)],
				["shift", "is", "set"],
			],
			pluck="shift",
		)
		if s
	}
	retired = []
	for shift in sorted(shifts - marking):
		row = shift_type.get_automation_attendance(employee, day, shift)
		if row is None:
			continue
		row.flags = getattr(row, "flags", None) or frappe._dict()
		row.flags.ignore_permissions = True
		row.cancel()
		retired.append(row.name)
		logger.info(
			"[day_remark] %s on %s: %s no longer has evidence under %s, cancelled",
			employee,
			day,
			row.name,
			shift,
		)
	return retired
