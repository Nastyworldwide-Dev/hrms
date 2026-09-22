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

RE-ENTRY: an automatic pass (endgame, recovery, ERP backfill, the hourly job)
re-stamps punches in bulk and rebuilds the same days itself. Its own punch
saves must not queue a SECOND rebuild of a day it is already rebuilding — two
rebuilds of one day take the same two row locks in opposite orders and
deadlock (16 Sep 2026, two Error Logs, MariaDB 1213). A pass declares the
employee-days it owns with `rebuilding()`; `remark_day_after_commit` refuses
those and only those. See the lock-order note in employee_checkin.py.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from functools import partial
from random import uniform
from time import sleep

import frappe
from frappe.utils import getdate

from hrms.hr.doctype.shift_type.shift_type import lock_employee_row
from hrms.utils.timezone import employee_now

logger = logging.getLogger(__name__)

JOB_METHOD = "hrms.utils.day_remark.remark_day"

#: Set on `frappe.flags` while an automatic pass rebuilds these employee-days
#: itself. Keys are "<employee>::<YYYY-MM-DD>". Request-local by nature, so it
#: silences only the pass's own punch saves — HR's edit and a real employee
#: punch run in their own request and queue as ever.
REBUILD_FLAG = "attendance_rebuild_in_progress"


def _key(employee, day) -> str:
	return f"{employee}::{getdate(day)}"


# isinstance, not truthiness: where frappe is stubbed `flags` is a mock whose
# `.get` answers another mock — truthy — and every day would read as owned.
def _owned() -> set:
	flags = getattr(frappe, "flags", None)
	current = flags.get(REBUILD_FLAG) if hasattr(flags, "get") else None
	return current if isinstance(current, set) else set()


def owned_by_an_automatic_pass(employee, day) -> bool:
	"""Is a pass in this worker already rebuilding this employee-day itself?"""
	return _key(employee, day) in _owned()


@contextmanager
def rebuilding(employee, *days):
	"""Declare these employee-days the caller's own work for the length of the block.

	Whoever suppresses the re-mark does the re-mark: a pass only takes a day
	under this if it rebuilds that day itself before the block ends.
	"""
	flags = frappe.flags
	before = _owned()
	flags[REBUILD_FLAG] = before | {_key(employee, day) for day in days if day}
	logger.debug("[day_remark] %s owns %s", employee, flags[REBUILD_FLAG] - before)
	try:
		yield
	finally:
		flags[REBUILD_FLAG] = before


def also_rebuilding(employee, day) -> None:
	"""Add one more employee-day to the pass already running — a punch re-stamped
	onto another day, whose day the pass could not name before it moved. Outside
	a pass this does nothing, so a lone re-stamp still queues its re-mark."""
	current = _owned()
	if not current:
		return
	frappe.flags[REBUILD_FLAG] = current | {_key(employee, day)}
	logger.debug("[day_remark] the running pass also owns %s on %s", employee, day)


def remark_day_after_commit(employee, day, reason, *, hr_asked=False, requests_ok=False) -> bool:
	"""Queue the engine's re-mark of `employee` on `day` for after commit. False when
	there is nothing to queue: no employee or day, the day is today or later, or an
	automatic pass in this worker is rebuilding that day itself.

	`hr_asked` / `requests_ok` carry the SAME authority the Fix Day screen
	carries, for a caller that has it. Default False, so the nightly job and
	every ordinary punch save keep the protections exactly as they were: a day a
	person keyed by hand is still held against automation that nobody asked for.
	Owner ruling, 22 Sep 2026 (option B): the wrong-shift repair DOES have it,
	because the hand-keyed rows it overwrites were keyed on top of a lying
	stamp — "despite manual hr effort, it might still do wrong due to this wrong
	mechanism". Money is not waived by either flag: a submitted Salary Slip or
	submitted Overtime Details still holds the day (`_repair_financial_dependency`)."""
	if not employee or not day:
		return False
	day = getdate(day)
	if day >= employee_now(employee).date():
		logger.info("[day_remark] %s on %s (%s) is today: left to the hourly job", employee, day, reason)
		return False
	if owned_by_an_automatic_pass(employee, day):
		logger.info(
			"[day_remark] %s on %s (%s) is being rebuilt by the pass that changed it: not queued again",
			employee,
			day,
			reason,
		)
		return False
	frappe.db.after_commit.add(
		partial(_enqueue, employee, str(day), reason, hr_asked=hr_asked, requests_ok=requests_ok)
	)
	logger.info("[day_remark] %s on %s queued after commit: %s", employee, day, reason)
	return True


def _enqueue(employee, day, reason, hr_asked=False, requests_ok=False):
	# ceiling: a job already RUNNING for the day drops this one (deduplicate), upgrade:
	# re-queue from the job's end if a change lands mid-run; the hourly/nightly read it meanwhile
	#
	# The authority is IN the job id. Two queues of one day that carry different
	# authority are two different questions — deduplicating an authoritative
	# re-mark into a plain one already waiting would silently answer the
	# stronger question with the weaker one. The ordinary id is unchanged, so a
	# job queued before this deploy still deduplicates against its successors.
	authority = "".join(sorted(k for k, on in (("hr", hr_asked), ("req", requests_ok)) if on))
	job_id = f"day-remark::{employee}::{day}" + (f"::{authority}" if authority else "")
	frappe.enqueue(
		JOB_METHOD,
		queue="short",
		job_id=job_id,
		deduplicate=True,
		employee=employee,
		day=day,
		reason=reason,
		hr_asked=hr_asked,
		requests_ok=requests_ok,
		# This IS the job, never a request, whatever authority it carries.
		# `remark_day` defaults `inline` to `hr_asked`, and an inline unit does
		# not retry a deadlock — at the worker that would surface as a lost
		# transaction instead of a retry.
		inline=False,
	)


def punch_day(checkin):
	"""(employee, shift day) of an Employee Checkin, or (None, None) when it is gone."""
	row = frappe.db.get_value("Employee Checkin", checkin, ["employee", "shift_start", "time"], as_dict=True)
	if not row:
		return None, None
	return row.employee, getdate(row.shift_start or row.time)


#: MariaDB: 1213 deadlock, 1205 lock-wait timeout. Either way the transaction is
#: gone — not just the statement — so the whole unit has to be run again.
LOST_TRANSACTION_CODES = (1205, 1213)
#: Tries per unit, and the base of the jittered wait between them.
DEADLOCK_ATTEMPTS = 3
DEADLOCK_BACKOFF = 0.2


def _lost_types() -> tuple:
	pair = (getattr(frappe, "QueryDeadlockError", None), getattr(frappe, "QueryTimeoutError", None))
	return tuple(t for t in pair if isinstance(t, type))


def is_lost_transaction(exc) -> bool:
	"""A deadlock or lock-wait timeout, by class or by MariaDB's own error code."""
	args = getattr(exc, "args", None)
	return isinstance(exc, _lost_types()) or (bool(args) and args[0] in LOST_TRANSACTION_CODES)


def despite_deadlock(unit, describe, attempts=DEADLOCK_ATTEMPTS, give_up=None):
	"""Run `unit`, and run it AGAIN when a deadlock took the transaction with it.

	Every unit here re-reads the day and re-marks it from scratch, so running it
	twice writes what running it once would have; and the alternative to a retry
	is a day nobody marks. After `attempts` the loss is recorded ONCE and
	`give_up` answers — the day is left to the nightly pass, and nothing raises
	into the worker, where it would only become another Error Log.
	"""
	for attempt in range(1, attempts + 1):
		try:
			return unit()
		except Exception as exc:
			if not is_lost_transaction(exc):
				raise
			frappe.db.rollback()
			if attempt >= attempts:
				logger.error(
					"[day_remark] %s: deadlocked %d times; left for the nightly pass", describe, attempts
				)
				_record_deadlock(describe, attempts)
				return give_up() if give_up else None
			logger.warning("[day_remark] %s: deadlock on try %d of %d; retrying", describe, attempt, attempts)
			sleep(uniform(DEADLOCK_BACKOFF, DEADLOCK_BACKOFF * 2 * attempt))


def _record_deadlock(describe, attempts) -> None:
	"""One Error Log for a day that lost every try — never one per attempt."""
	try:
		frappe.log_error(
			title="Day re-mark left for the nightly pass",
			message=f"{describe}: the database deadlocked {attempts} times",
		)
	except Exception:
		logger.exception("[day_remark] could not record the deadlock of %s", describe)


def remark_day(employee, day, reason="", hr_asked=False, inline=None, requests_ok=False):
	"""The job: re-mark one past employee-day through the engine, unless it is protected.

	The day is this job's own while it runs, so the links and skip stamps the
	engine writes under it cannot queue the same day a second time; and a
	deadlock against another writer is retried rather than raised at the worker.

	`inline` (default: `hr_asked`) says the caller is a REQUEST, not the job.
	There `despite_deadlock`'s full rollback would also drop the caller's own
	writes — Fix Day's taps and Comments — and the retry would re-mark the day
	on the old evidence while the caller logs ok (D-H1, 21 Sep 2026). So inline
	the unit runs once and a lost transaction propagates: the request rolls back
	as a whole and the person sees an error.
	"""
	day = getdate(day)
	if inline is None:
		inline = hr_asked
	if inline:
		logger.debug("[day_remark] %s on %s (%s): inline, no deadlock retry", employee, day, reason)
		return _remark_owning_the_day(employee, day, reason, hr_asked=hr_asked, requests_ok=requests_ok)
	return despite_deadlock(
		lambda: _remark_owning_the_day(employee, day, reason, hr_asked=hr_asked, requests_ok=requests_ok),
		f"{employee} on {day} ({reason})",
		give_up=lambda: {"action": "deadlocked"},
	)


def _remark_owning_the_day(employee, day, reason="", hr_asked=False, requests_ok=False):
	logger.debug("[day_remark] %s on %s: taking the day", employee, day)
	with rebuilding(employee, day):
		return _remark_once(employee, day, reason, hr_asked=hr_asked, requests_ok=requests_ok)


def _remark_once(employee, day, reason="", hr_asked=False, requests_ok=False):
	"""`hr_asked` waives ONLY the "a person made this row" hold, and only
	because HR is the one asking — see attendance_recovery.protected_reason.
	`requests_ok` (Fix days) lets an approved OT / Attendance Request day through:
	the request keeps its approval, the row is rebuilt from the punches."""
	from hrms.hr.doctype.shift_type import shift_type
	from hrms.utils import attendance_recovery as rec

	if _shift_still_running(employee, day):
		logger.info("[day_remark] %s on %s: shift still running, left to the hourly job", employee, day)
		return {"action": "running"}
	lock_employee_row(employee)
	held = rec._day_protection(employee, day, for_update=True, hr_asked=hr_asked, requests_ok=requests_ok)
	if held:
		logger.info("[day_remark] %s on %s held (%s): %s", employee, day, reason, held)
		return {"action": "held", "detail": held}
	if hr_asked:
		# HR's press brings the never-worse guard with it. There are two rebuild
		# paths here and only `attendance_recovery`'s own takes a savepoint,
		# compares the day before and after, and rolls back a rebuild that
		# lowered a submitted day. That was harmless while `owner_hold` refused
		# to rebuild an HR-owned row at all; `hr_asked` opens exactly that door,
		# so a day HR raised to Present by hand cannot come back Absent from a
		# recompute nobody was watching (review of b9794c65b).
		#
		# `_rebuild_under_guard`, not `guarded_rebuild`: the outer one takes the
		# day and retries deadlocks, and this is already inside both. With
		# `hr_asked` the guard judges and LOGS a lowered day but never rolls it
		# back: HR's edit always wins; the system recalculates (owner, 21 Sep).
		def remark(employee, day, apply):
			rec.release_to_automation(employee, day)
			return rec._remark_released_day(employee, day, apply)

		result = rec._rebuild_under_guard(employee, day, remark, source="hr_fix_day", hr_asked=True)
		if result.get("held"):
			logger.warning(
				"[day_remark] %s on %s rolled back by the never-worse guard (%s): %s",
				employee,
				day,
				reason,
				result["held"],
			)
			# No `rolled_back` flag beside it: nothing reads one, and `detail`
			# already says which guard spoke. A field kept for a screen that does
			# not exist yet is scaffolding, and scaffolding rots.
			return {"action": "held", "detail": result["held"]}
		source = "hr_fix_day"
	else:
		# The job is automatic, so the guard ROLLS BACK a re-mark that would
		# lower a submitted day and lists it (B-H6, 21 Sep 2026: this was the
		# most-used rebuild path and the only bare, unlogged one). Every
		# re-mark that marks is on the day-fix log as `day_remark` / `remark`.
		source = "day_remark"
		result = rec._rebuild_under_guard(
			employee, day, rec._remark_released_day, source=source, action="remark"
		)
		if result.get("held"):
			logger.warning(
				"[day_remark] %s on %s rolled back by the never-worse guard (%s): %s",
				employee,
				day,
				reason,
				result["held"],
			)
			# Return before `_retire_unmarkable_rows`: it reads the result that
			# was just undone and would cancel the row the guard protected.
			return {"action": "held", "detail": result["held"]}
	retired = _retire_unmarkable_rows(employee, day, result, shift_type, source=source)
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


def _retire_unmarkable_rows(employee, day, result, shift_type, source="day_remark") -> list:
	"""A punch-owned row the engine would no longer write (every punch of its shift
	rejected or skipped, or a rest day left without an approved pair) is cancelled,
	so the day reads what the engine marks from scratch. HR's, leave and mirrored
	rows are never found (get_automation_attendance); protected days never get here.
	Each cancellation is on the day-fix log as `retire` under `source`."""
	from hrms.utils import attendance_recovery as rec

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
		before = rec._row_summary(row)
		row.cancel()
		retired.append(row.name)
		rec.log_day_fix(employee, day, "retire", before=before, after=None, source=source)
		logger.info(
			"[day_remark] %s on %s: %s no longer has evidence under %s, cancelled",
			employee,
			day,
			row.name,
			shift,
		)
	if not shifts and not _any_punch_on(employee, day):
		retired.extend(_retire_emptied_day(employee, day))
	return retired


def _any_punch_on(employee, day) -> bool:
	"""A punch whose clock falls on the day, whatever its stamp (a cleared one has no shift_start)."""
	start = datetime.combine(day, time.min)
	found = bool(
		frappe.db.exists(
			"Employee Checkin",
			[["employee", "=", employee], ["time", ">=", start], ["time", "<", start + timedelta(days=1)]],
		)
	)
	logger.info(
		"[day_remark] %s on %s: %s", employee, day, "punches by clock" if found else "no punch at all"
	)
	return found


def _retire_emptied_day(employee, day) -> list:
	"""The day has no punch at all any more: every SYSTEM row on it is retired.

	The roster re-stamp (hrms/utils/restamp.py) can move a day's only punch
	onto another day and release its link; the shift loop above never sees
	that shift, so the stale row — old out_time, dangling link — survived
	(21 Sep 2026). A typed row (auto_attendance=0), a leave or request row,
	and one the owner check calls a person's are left alone.
	"""
	from hrms.utils import attendance_recovery as rec

	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": day,
			"docstatus": 1,
			"auto_attendance": 1,
			"synced_from_instance": ("is", "not set"),
			"leave_type": ("is", "not set"),
			"attendance_request": ("is", "not set"),
			"modify_half_day_status": 0,
			"status": ("!=", "On Leave"),
		},
		fields=[
			"name",
			"attendance_date",
			"shift",
			"status",
			"working_hours",
			"in_time",
			"out_time",
			"owner",
		],
	)
	retired = []
	for row in rows:
		hold = rec.owner_hold(row)
		if hold:
			logger.info("[day_remark] %s on %s: emptied day, %s kept: %s", employee, day, row["name"], hold)
			continue
		doc = frappe.get_doc("Attendance", row["name"])
		doc.flags.ignore_permissions = True
		doc.cancel()
		retired.append(row["name"])
		rec.log_day_fix(
			employee,
			day,
			"retire",
			before=rec._row_summary(row),
			after={"reason": "no punches left on the day"},
			source="day_remark",
		)
		logger.info(
			"[day_remark] %s on %s: %s retired, no punches left on the day", employee, day, row["name"]
		)
	return retired
