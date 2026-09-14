"""A punch saved without a shift is a punch the hourly job never reads.

4 September 2026: IN 3 Sep 08:48 on a 9-6 shift, OUT 4 Sep 01:04. The OUT was
saved before f6528e423 (10 Sep) taught fetch_shift that a check-out closes the
shift of the check-in it follows, so it was filed off-shift. The hourly job
reads only punches that carry a shift and no attendance
(ShiftType.get_employee_checkins), so the day stayed "Half Day, no out, 0h"
forever. Re-running today's fetch_shift on that OUT and letting the job run
again rebuilds the day as Present 16.07h (probed on a real site, 14 Sep).

Two entry points, one rule — the resolution is fetch_shift itself
(hrms/overrides/employee_checkin_override.py), never a copy of it:

* `heal_recent_offshift_punches` — called by the hourly attendance job before
  it reads punches. Check-outs only, at most RECENT_DAYS (2) days old. Such a
  check-out takes the shift of an IN up to SESSION_WINDOW (20 h) before it, so
  the day the job then re-marks can lie up to ~2 days + 20 h back from now.
* `heal_offshift_punches` — the owner-gated historical run. Dry run by default;
  days before `not_before` (the current 16th-to-15th payroll cycle unless given)
  are held back, because payroll here is external and may already be closed.

Nothing is deleted. The punch gets the whole shift stamp and the hourly job's
own cancel-and-rebuild path (ShiftType.mark_attendance_for_shift_logs) rewrites
the day. Days a payout already depends on are held back, as in the Attendance
Day Audit repair.

Re-dating a punch also un-shields its clock date. The absent sweep dates a
shiftless punch by its clock date, so that day was never swept; once the punch
belongs to the shift day before, the clock day can be marked Absent — exactly
as for a punch saved under today's rule. The manual run reports that day as
`leaves_day`. Its `may_become_absent` flag is deliberately NOT a prediction of
the sweep: it is True for EVERY healed punch. Stamping a shift also removes a
punch from the sweep of any non-overlapping shift type, so even a punch that
stays on its own date can expose that date under a second assignment. Three
attempts to model which rows shield a day (the roster on the day the sweep
runs, which shift each punch counts under, whether the date moved) each hid
days the sweep then marked. The day's attendance, punches and assignments are
listed for HR instead.
"""

import logging
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

from hrms.overrides.company_scope import require_unfenced
from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency
from hrms.utils.attendance_day_audit import _job_can_read
from hrms.utils.filing_window import cycle_start

logger = logging.getLogger(__name__)

#: A historical run with no from_date looks back this far (or to the earliest
#: Process Attendance After, whichever is later).
DEFAULT_LOOKBACK_DAYS = 35
#: A historical run refuses a wider window: one request re-resolves every punch in it.
MAX_WINDOW_DAYS = 62
#: The hourly pass only looks this far back. Older days are the owner's call.
RECENT_DAYS = 2
# ceiling: the hourly pass re-resolves at most RECENT_LIMIT shiftless check-outs,
# newest first; upgrade: page by time if an Error Log titled "Off-shift punch
# heal hit its limit" ever appears.
RECENT_LIMIT = 200
ROW_SAVEPOINT = "offshift_punch_heal_row"
SAVEPOINT = "offshift_punch_heal"
FAILURE_TITLE = "Off-shift punch heal failed"
MAY_BECOME_ABSENT = (
	"this day loses this punch; the attendance sweep may mark it Absent — check the rows listed"
)
#: A deadlock (1213) rolls back the whole transaction, so every earlier save in
#: this pass is gone. A lock wait timeout (1205, QueryTimeoutError) by default
#: rolls back only the statement; re-raising it too is deliberately
#: over-cautious — it aborts the pass and loses nothing but an hour's delay.
LOST_TRANSACTION_CODES = (1205, 1213)

ATTENDANCE_FIELDS = ["name", "status", "docstatus", "shift", "in_time", "out_time", "working_hours"]


def _candidates(start, end=None, employee=None, log_type=None, limit=0, order="asc") -> list:
	"""Local, unlinked punches with no shift, in [start, end). Every filter is
	one the job's own query uses, so the rows are exactly the ones it skips."""
	logger.debug(
		"[offshift_punch_heal] candidates %s..%s employee=%s log_type=%s limit=%s",
		start,
		end,
		employee,
		log_type,
		limit,
	)
	filters = [
		["shift", "is", "not set"],
		["attendance", "is", "not set"],
		# Mirrored punches belong to their source instance (hrms/sync/write_block.py).
		["synced_from_instance", "is", "not set"],
		["time", ">=", start],
	]
	if end:
		filters.append(["time", "<", end])
	if employee:
		filters.append(["employee", "=", employee])
	if log_type:
		filters.append(["log_type", "=", log_type])
	return frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["name"],
		order_by=f"time {order}",
		limit_page_length=limit,
	)


def _lost_transaction(exc) -> bool:
	"""A deadlock or lock timeout: the transaction is gone, not just this row."""
	lost_types = tuple(
		t
		for t in (getattr(frappe, "QueryDeadlockError", None), getattr(frappe, "QueryTimeoutError", None))
		if isinstance(t, type)
	)
	lost = isinstance(exc, lost_types) or (bool(exc.args) and exc.args[0] in LOST_TRANSACTION_CODES)
	if lost:
		logger.warning("[offshift_punch_heal] transaction lost: %s", type(exc).__name__)
	return lost


def _resolve(name):
	"""The punch with today's fetch_shift applied in memory, or None when the
	rule still gives it no shift. Nothing is written here. One bad row never
	stops the rest — except a lost transaction, which is re-raised: the saves
	before it are gone, and reporting them healed would be a lie."""
	try:
		punch = frappe.get_doc("Employee Checkin", name)
		if punch.shift or punch.attendance:
			return None
		punch.fetch_shift()
	except Exception as exc:
		if _lost_transaction(exc):
			raise
		if isinstance(exc, frappe.ValidationError):
			# e.g. a strict log-type shift and a punch without a log type: leave it.
			logger.warning("[offshift_punch_heal] %s cannot be resolved: %s", name, exc)
		else:
			logger.exception("[offshift_punch_heal] %s failed to re-resolve; moving on", name)
		return None
	return punch if punch.shift else None


def _attendance_on(employee, day) -> list:
	logger.debug("[offshift_punch_heal] attendance of %s on %s", employee, day)
	return frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": day, "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
		order_by="creation asc",
	)


def _entry(punch) -> dict:
	shift_date = getdate(punch.shift_start or punch.time)
	logger.debug("[offshift_punch_heal] %s resolves to %s on %s", punch.name, punch.shift, shift_date)
	return {
		"checkin": punch.name,
		"employee": punch.employee,
		"time": str(punch.time),
		"log_type": punch.log_type,
		"shift": punch.shift,
		"shift_date": str(shift_date),
		"attendance": _attendance_on(punch.employee, shift_date),
	}


def _other_punches_on(employee, day, exclude) -> list:
	"""Informational only: other punches on `day` by clock date or shift day."""
	start = datetime.combine(day, datetime.min.time())
	end = start + timedelta(days=1)
	found = {}
	for field in ("time", "shift_start"):
		for row in frappe.get_all(
			"Employee Checkin",
			filters=[
				["employee", "=", employee],
				["name", "!=", exclude],
				[field, ">=", start],
				[field, "<", end],
			],
			fields=["name", "time", "shift", "shift_start"],
		):
			found.setdefault(row.name, row)
	logger.debug("[offshift_punch_heal] %s has %d other punch(es) on %s", employee, len(found), day)
	return sorted(found.values(), key=lambda row: get_datetime(row.time))


def _assignments_on(employee, day) -> list:
	"""Informational only: which shift assignments cover `day` today."""
	logger.debug("[offshift_punch_heal] shift assignments of %s on %s", employee, day)
	return frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active", "start_date": ["<=", day]},
		or_filters=[["end_date", ">=", day], ["end_date", "is", "not set"]],
		fields=["name", "shift_type"],
	)


def _leaves_day(punch, shift_date) -> dict | None:
	"""The clock-date day this punch may stop shielding from the absent sweep.

	Flagged for EVERY healed punch, on purpose. A shiftless punch shields its
	clock date for every shift type's sweep; once it carries a shift it is
	skipped by the sweep of any shift type that does not overlap it, so even a
	punch that stays on its own date can expose that date under a second,
	non-overlapping assignment. No protection logic: the day's rows are listed
	so HR can judge; nothing here decides for them."""
	clock_day = getdate(punch.time)
	logger.info("[offshift_punch_heal] %s leaves %s on %s", punch.name, punch.employee, clock_day)
	return {
		"employee": punch.employee,
		"date": str(clock_day),
		"may_become_absent": True,
		"label": MAY_BECOME_ABSENT,
		"attendance": _attendance_on(punch.employee, clock_day),
		"other_punches": _other_punches_on(punch.employee, clock_day, punch.name),
		"shift_assignments": _assignments_on(punch.employee, clock_day),
	}


def _heal(start, end=None, *, dry_run, for_update, not_before=None, report_exposure=False, **query):
	"""Re-resolve each candidate; write the ones the job will then read.

	`query` narrows the candidates (employee, log_type, limit, order). Oldest
	first by default: a check-out resolves against the check-in it closes, so an
	earlier punch healed in this pass is visible to a later one.
	"""
	logger.debug("[offshift_punch_heal] pass dry_run=%s not_before=%s %s", dry_run, not_before, query)
	rows = _candidates(start, end, **query)
	healed, held_back, not_readable = [], [], []
	for row in rows:
		punch = _resolve(row.name)
		if punch is None:
			continue
		entry = _entry(punch)
		if not _job_can_read(punch):
			# Stamping a shift the job never processes changes nothing but the row.
			not_readable.append(entry)
			continue
		if report_exposure:
			entry["leaves_day"] = _leaves_day(punch, entry["shift_date"])
		if not_before and getdate(entry["shift_date"]) < not_before:
			# The shift day is never after the clock day, so this covers both.
			entry["held_because"] = f"before {not_before}: that payroll cycle may be closed"
			held_back.append(entry)
			continue
		if not dry_run:
			# One row that cannot be written (a stale link, a concurrent save) must
			# not roll back every other employee's heal in this pass.
			frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			on_shift = next((a.name for a in entry["attendance"] if a.shift == punch.shift), None)
			if _repair_financial_dependency(
				punch.employee, entry["shift_date"], on_shift, for_update=for_update
			):
				# The rebuild would be refused by the job's financial guard, which then
				# skip-stamps the whole day. HR corrects a paid day by hand.
				entry["held_because"] = "approved overtime or submitted payroll depends on the day"
				held_back.append(entry)
				continue
			if not dry_run:
				# The same write the Attendance Day Audit repair and probe B3 make:
				# through the document, validate skipped (geofence and duplicate checks
				# judge a live punch, not a re-stamp of a stored one).
				punch.flags.ignore_validate = True
				punch.flags.ignore_permissions = True
				punch.save()
				punch.add_comment(
					"Comment",
					_(
						"Off-shift punch heal: shift {0} re-resolved for {1}; the hourly job rebuilds that day."
					).format(punch.shift, entry["shift_date"]),
				)
		except Exception as exc:
			if dry_run or _lost_transaction(exc):
				raise
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			logger.exception("[offshift_punch_heal] could not write %s; skipped", punch.name)
			entry["held_because"] = f"could not be written: {exc}"
			not_readable.append(entry)
			continue
		healed.append(entry)
	logger.info(
		"[offshift_punch_heal] %s..%s dry_run=%s: %d candidate(s), %d healed, %d held back, %d unreadable",
		start,
		end,
		dry_run,
		len(rows),
		len(healed),
		len(held_back),
		len(not_readable),
	)
	return {
		"candidates": len(rows),
		"healed": healed,
		"held_back": held_back,
		"not_readable": not_readable,
	}


def _window(from_date, to_date):
	"""[start, end) as datetimes, refused when wider than MAX_WINDOW_DAYS."""
	end_day = getdate(to_date) if to_date else getdate(now_datetime())
	if from_date:
		start_day = getdate(from_date)
	else:
		start_day = end_day - timedelta(days=DEFAULT_LOOKBACK_DAYS)
		earliest = frappe.get_all(
			"Shift Type",
			filters={"enable_auto_attendance": 1, "process_attendance_after": ["is", "set"]},
			pluck="process_attendance_after",
			order_by="process_attendance_after asc",
			limit_page_length=1,
		)
		if earliest:
			start_day = max(start_day, getdate(earliest[0]))
	if start_day > end_day:
		frappe.throw(_("From Date must not be after To Date."))
	if (end_day - start_day).days > MAX_WINDOW_DAYS:
		frappe.throw(_("Heal at most {0} days per run.").format(MAX_WINDOW_DAYS))
	start = datetime.combine(start_day, datetime.min.time())
	return start, datetime.combine(end_day, datetime.min.time()) + timedelta(days=1)


@frappe.whitelist()
def heal_offshift_punches(from_date=None, to_date=None, dry_run=1, employee=None, not_before=None) -> dict:
	"""Give shiftless local punches the shift today's rule gives them, then let
	each affected shift type re-mark its days. Dry run by default.

	`not_before`: shift days before it are held back (reported, never written).
	Defaults to the start of the current 16th-to-15th cycle — no attendance lock
	exists in this app, and payroll runs outside it.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced(_("re-resolve punches across every company"))
	dry_run = cint(dry_run)
	start, end = _window(from_date, to_date)
	not_before = getdate(not_before) if not_before else cycle_start(getdate(now_datetime()))
	result = _heal(
		start,
		end,
		dry_run=dry_run,
		for_update=not dry_run,
		employee=employee,
		not_before=not_before,
		report_exposure=True,
	)
	shift_types = sorted({entry["shift"] for entry in result["healed"]})
	if not dry_run and shift_types:
		frappe.enqueue(
			"hrms.utils.offshift_punch_heal.process_shift_types",
			queue="long",
			timeout=3600,
			shift_types=shift_types,
			enqueue_after_commit=True,
			now=bool(frappe.flags.in_test),
		)
	logger.info(
		"[offshift_punch_heal] run by %s dry_run=%s employee=%s not_before=%s: %d healed, %d held, shift types %s",
		frappe.session.user,
		dry_run,
		employee,
		not_before,
		len(result["healed"]),
		len(result["held_back"]),
		shift_types,
	)
	return {
		"dry_run": bool(dry_run),
		"from_date": str(start.date()),
		"to_date": str((end - timedelta(days=1)).date()),
		"not_before": str(not_before),
		"shift_types": shift_types,
		**result,
	}


def process_shift_types(shift_types) -> None:
	"""What the hourly job does, for the shift types a heal touched."""
	for name in shift_types:
		logger.info("[offshift_punch_heal] re-marking attendance for %s", name)
		frappe.get_doc("Shift Type", name).process_auto_attendance()


def _undo_pass() -> None:
	"""Roll the hourly pass back without raising."""
	try:
		frappe.db.rollback(save_point=SAVEPOINT)
	except Exception:
		# After a deadlock MariaDB has already dropped the whole transaction,
		# savepoint included, and rolling back to it raises 1305. The pass runs
		# first in the job, so a plain rollback loses nothing else.
		logger.warning("[offshift_punch_heal] savepoint gone; rolling back the transaction")
		try:
			frappe.db.rollback()
		except Exception:
			logger.exception("[offshift_punch_heal] rollback failed")


def heal_recent_offshift_punches() -> int:
	"""The hourly pass, run before the job reads punches. Never raises: a failure
	here must not stop attendance being marked."""
	start = get_datetime(now_datetime()) - timedelta(days=RECENT_DAYS)
	try:
		frappe.db.savepoint(SAVEPOINT)
		# Check-outs only: an IN has no session to inherit from, and one saved
		# today already went through the current rule. Newest first, so a backlog
		# of genuinely off-shift punches can never starve a fresh one.
		result = _heal(start, dry_run=0, for_update=True, log_type="OUT", limit=RECENT_LIMIT, order="desc")
		if result["candidates"] >= RECENT_LIMIT:
			logger.warning("[offshift_punch_heal] hourly pass hit the limit of %d", RECENT_LIMIT)
			frappe.log_error(
				title="Off-shift punch heal hit its limit",
				message=f"{result['candidates']} shiftless check-outs in the last 2 days; limit {RECENT_LIMIT}.",
			)
		if not frappe.in_test:
			# Releases the payroll row locks taken above before the long job starts.
			frappe.db.commit()  # nosemgrep
	except Exception:
		logger.exception("[offshift_punch_heal] hourly pass failed; attendance marking continues")
		_undo_pass()
		try:
			frappe.log_error(title=FAILURE_TITLE)
		except Exception:
			logger.exception("[offshift_punch_heal] could not record the failure")
		return 0
	return len(result["healed"])
