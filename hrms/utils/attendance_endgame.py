"""The whole attendance repair, performed by the system itself — Nabil, 16 Sep 2026.

"too much mechanical work for us and for HR — it should be done automatically by
the system at once, except the relinking screen I asked for."

Everything the repair needed a person for is here, in one background job:

	(a) give system-made Attendance rows their `auto_attendance` tick back
	    (hrms/utils/attendance_ownership.py);
	(b) compare this hub's punches with the old ERP's and copy, insert-only,
	    what is missing for 1 Aug → 3 Sep (hrms/sync/erp_backfill.py);
	(c) run every automatic recovery step for 1 Aug → yesterday
	    (hrms/utils/attendance_auto_recovery.py — its semantics, not a copy of
	    them: this module calls `_run`, so there is one implementation of the
	    order, the protections and the per-step rollback);
	(d) recount OT over the whole window, after every rebuild above;
	(e) send HR ONE summary in plain English.

Nothing here waits to be started. The switches the earlier releases shipped are
EMERGENCY STOPS now, not start gates: `attendance_ownership_relabel` and
`attendance_erp_backfill` read as ON while their Custom Field does not exist, and
`attendance_endgame_stop` halts this orchestrator between steps. HR turns one OFF
to stop the machine; HR never turns one ON to start it.

The pass is chunked (31 days), capped (`MAX_CHUNKS_PER_PASS` step-chunks) and
resumable: the marker is written BEFORE each chunk, so a worker a deploy kills
mid-chunk simply redoes that chunk next time — every step is idempotent. The
scheduler calls this every night, so an interrupted repair finishes itself
without anyone noticing it had stopped.

Every entry the run writes to HR Day Fix Log carries the SAME `run` id (through
`attendance_recovery.log_day_fix`, which reads `current_run()`), so "undo the
whole run" is one filter — `undo_run` — and not an archaeology exercise.

	PYTHONPATH=. python3 hrms/tests/test_attendance_endgame.py
"""

import json
import logging
from datetime import timedelta
from uuid import uuid4

import frappe
from frappe.utils import cint, getdate, now_datetime, nowdate

from hrms.overrides.remote_checkin_request_hooks import notify_hr
from hrms.sync import erp_backfill as backfill
from hrms.utils import attendance_auto_recovery as auto
from hrms.utils import attendance_ownership as own
from hrms.utils import attendance_recovery as rec

logger = logging.getLogger(__name__)

#: The owner's order. Each step covers the WHOLE window before the next begins,
#: so the OT recount sees every rebuild the earlier steps made.
STEPS = ("relabel", "punches", "recovery", "duplicates", "ot")
CHUNK_DAYS = 31
#: Step-chunks per pass. A killed or capped pass leaves a marker and the next
#: one carries on, so no single job has to survive the whole month's repair.
MAX_CHUNKS_PER_PASS = 24
#: HR Settings Check; ABSENT = run. The one emergency stop for the orchestrator.
STOP_SWITCH = "attendance_endgame_stop"
#: Default Value written when the whole repair finished.
DONE_MARK = "attendance_endgame_done"
#: Default Value holding the resume marker (JSON) while a run is unfinished.
STATE_MARK = "attendance_endgame_state"
JOB_ID = "attendance_endgame_once"
UNDO_SAVEPOINT = "attendance_endgame_undo"
TITLE_PREFIX = "Attendance endgame"
#: Only a rebuild entry records a before-state that can be put back.
UNDOABLE = ("rebuild",)

#: The run every step of the current pass writes under. `log_day_fix` reads it.
_CURRENT_RUN = None


def current_run():
	"""The run id the orchestrator is working under, or None outside a run.

	`attendance_recovery.log_day_fix` asks this, so every HR Day Fix Log entry a
	step writes carries the same `run` — which is what makes `undo_run` possible.
	"""
	return _CURRENT_RUN


def stopped() -> bool:
	"""HR Settings `attendance_endgame_stop`: ticked = halt. An absent field runs.

	An emergency stop, not a start gate — and a settings row that cannot be read
	is not evidence of a stop.
	"""
	try:
		return bool(cint(frappe.get_single("HR Settings").get(STOP_SWITCH)))
	except Exception:
		logger.exception("[attendance_endgame] could not read %s; carrying on", STOP_SWITCH)
		return False


# --- window and resume marker ---------------------------------------------------------


def _chunks(start, end):
	"""Windows of at most CHUNK_DAYS days, oldest first."""
	while start <= end:
		stop = min(end, start + timedelta(days=CHUNK_DAYS - 1))
		yield start, stop
		start = stop + timedelta(days=1)


def _window(from_date, to_date) -> tuple:
	"""[start, end]: never before the repair floor, never past yesterday."""
	yesterday = getdate(nowdate()) - timedelta(days=1)
	start = max(getdate(from_date), rec.REPAIR_FLOOR) if from_date else rec.REPAIR_FLOOR
	end = min(getdate(to_date), yesterday) if to_date else yesterday
	logger.info("[attendance_endgame] window %s..%s", start, end)
	return start, end


def _counts(previous=None) -> dict:
	base = {
		"relabelled": 0,
		"punches_missing": 0,
		"punches_copied": 0,
		"days_rebuilt": 0,
		"left_alone": 0,
		"needs_hr": 0,
		"rows_cancelled": 0,
		"ot_rows": 0,
		"notes": [],
	}
	base.update(previous or {})
	return base


def _new_run_id() -> str:
	return f"ENDGAME-{nowdate()}-{uuid4().hex[:6]}"


def _load_state() -> dict:
	"""The unfinished run's marker, or {} for a fresh start. Never raises."""
	try:
		raw = frappe.db.get_default(STATE_MARK)
		state = json.loads(raw) if raw else None
		if isinstance(state, dict) and state.get("run"):
			logger.info(
				"[attendance_endgame] resuming %s at %s/%s",
				state["run"],
				state.get("step"),
				state.get("cursor"),
			)
			return state
	except Exception:
		logger.exception("[attendance_endgame] unreadable resume marker; starting a fresh run")
	return {}


def _save_state(run, step, cursor, counts, errors) -> None:
	"""Write the marker BEFORE the chunk it names, so a kill costs one chunk."""
	try:
		frappe.db.set_default(
			STATE_MARK,
			json.dumps(
				{"run": run, "step": step, "cursor": str(cursor), "counts": counts, "errors": errors},
				default=str,
			),
		)
		frappe.db.commit()
	except Exception:
		logger.exception("[attendance_endgame] could not save the resume marker")


def _clear_state() -> None:
	try:
		frappe.db.set_default(STATE_MARK, None)
	except Exception:
		logger.exception("[attendance_endgame] could not clear the resume marker")


# --- the steps ------------------------------------------------------------------------


def _tally_held(held, counts) -> None:
	"""A held-back day is either HR's to fix or one we left alone on purpose."""
	for entry in held or []:
		if auto.needs_hr(entry):
			counts["needs_hr"] += 1
		else:
			counts["left_alone"] += 1


def _step_relabel(start, end, counts, errors) -> None:
	"""(a) System-made rows get their tick back, so the fixes stop reading them as HR's."""
	out = own.relabel_system_rows(start, end, dry_run=0) or {}
	if out.get("refused"):
		counts["notes"].append(f"relabel {start}..{end}: {out['refused']}")
		return
	counts["relabelled"] += len(out.get("changed") or [])


def _recount_ot(start, end) -> dict:
	"""The OT recount for one chunk, through recovery's own planner and applier."""
	win = rec.recovery_window(start, end, getdate(nowdate()))
	plan = rec._PLANNERS["ot_recount"](win, for_update=True)
	return rec._APPLIERS["ot_recount"](win, plan)


def _step_punches(start, end, counts, errors) -> None:
	"""(b) What the old ERP holds and this hub never got, copied insert-only.

	The hub owns everything from the cutover, so this step stops at 3 September
	however far the run's window reaches. The parity read comes first and is
	reported even when it fails: it is what tells HR how much was missing.
	"""
	stop = min(end, backfill.LAST_DAY)
	if start > stop:
		logger.info("[attendance_endgame] %s..%s is past the cutover; no punch to copy", start, end)
		return
	try:
		report = backfill.parity(start, stop) or {}
		counts["punches_missing"] += cint((report.get("counts") or {}).get("hub_missing_punches"))
	except Exception as exc:
		logger.exception("[attendance_endgame] parity %s..%s failed", start, stop)
		errors.append(f"parity {start}..{stop}: {exc}")
	out = backfill.backfill_punches(start, stop, dry_run=0) or {}
	counts["punches_copied"] += len(out.get("inserted") or [])
	counts["days_rebuilt"] += len(out.get("rebuilt") or [])
	_tally_held(out.get("held_back"), counts)
	if out.get("note"):
		counts["notes"].append(f"punches {start}..{stop}: {out['note']}")


def _step_recovery(start, end, counts, errors) -> None:
	"""(c) Every automatic recovery step, in recovery's own order.

	`auto._run` IS the semantics — the step order, the per-step rollback, the day
	protections and the HR/on-purpose split all live there. Duplicating any of it
	here would give the repair two implementations that could disagree.
	"""
	summary = auto._run(start, end) or {}
	for tally in (summary.get("steps") or {}).values():
		counts["days_rebuilt"] += cint(tally.get("done"))
	counts["needs_hr"] += cint(summary.get("hr_days"))
	counts["left_alone"] += cint(summary.get("protected_days"))
	for step in summary.get("stopped_at") or []:
		detail = (summary.get("steps") or {}).get(step, {}).get("error")
		errors.append(f"recovery step {step} {start}..{end}: {detail}")


def _step_duplicates(start, end, counts, errors) -> None:
	"""(d) A day left holding two attendance rows goes back to one.

	`resolve_duplicate_rows` has existed, tested, since the backfill work — keep
	the row the day's punches are linked to, cancel a system-made duplicate, put
	a human-made one on HR's list — and until 17 Sep 2026 NOTHING called it. The
	recovery's `leftover_rows` removes only EMPTY leftovers on a rebuilt split
	day, so a day whose two rows both carry punches survived every pass. That is
	why the last release did not finish the job.

	Placed after `recovery` because the decision reads which punches link to
	which row, and the recovery is what links them; placed before `ot` because
	the recount must price the row that survived. It applies through the
	backfill's own switch and the recovery's day protections, so a paid, leave
	or HR-owned day is reported, never forced.
	"""
	out = backfill.resolve_duplicate_rows(start, end, dry_run=0) or {}
	cancelled = set(out.get("cancelled") or [])
	counts["rows_cancelled"] += len(cancelled)
	_tally_held(out.get("held_back"), counts)
	if out.get("note"):
		counts["notes"].append(f"duplicates {start}..{end}: {out['note']}")

	# Cancelling a row changes the day and nothing else would re-mark it: the
	# resolver only cancels. One deduplicated re-mark per day through the shared
	# engine, which keeps the protections and the ordering with every other
	# writer.
	from hrms.utils.day_remark import remark_day_after_commit

	for entry in out.get("days") or []:
		if not (cancelled & set(entry.get("cancel") or [])):
			continue
		try:
			remark_day_after_commit(
				entry.get("employee"), entry.get("date"), f"duplicate row cancelled ({start}..{end})"
			)
		except Exception:
			logger.exception(
				"[attendance_endgame] could not queue the re-mark of %s on %s",
				entry.get("employee"),
				entry.get("date"),
			)


def _step_ot(start, end, counts, errors) -> None:
	"""(d) OT recount, last, so it prices every day the earlier steps rebuilt."""
	out = _recount_ot(start, end) or {}
	counts["ot_rows"] += len(out.get("done") or [])
	_tally_held(out.get("held_back"), counts)


_RUNNERS = {
	"relabel": _step_relabel,
	"punches": _step_punches,
	"recovery": _step_recovery,
	"duplicates": _step_duplicates,
	"ot": _step_ot,
}


# --- the summary ----------------------------------------------------------------------


def _message(run, start, end, counts, errors, reason) -> str:
	"""What the machine did, in the words HR uses. One screen, no jargon."""
	lines = [
		f"The system repaired attendance by itself ({reason}). Nobody needs to run anything.",
		f"Window {start} → {end}; today is never touched.",
		"",
		f"Rows relabelled as made by the system: {counts['relabelled']}",
		f"Punches copied from the old system: {counts['punches_copied']}"
		+ (f" (of {counts['punches_missing']} missing)" if counts.get("punches_missing") else ""),
		f"Days rebuilt: {counts['days_rebuilt']}",
		f"Duplicate attendance rows cancelled (the day keeps the row its punches "
		f"are linked to): {counts['rows_cancelled']}",
		f"Days left alone on purpose (a leave, HR's own edit, or already paid): {counts['left_alone']}",
		f"Days that still need HR: {counts['needs_hr']} — open Shift Attendance and use Fix Day.",
		f"OT rows recounted: {counts['ot_rows']}",
		"",
		f"Run id: {run}",
		f"To undo everything this run changed: filter HR Day Fix Log by Run = {run}, "
		f'or run hrms.utils.attendance_endgame.undo_run("{run}").',
	]
	lines.extend(f"Could not finish: {note}" for note in errors or [])
	lines.extend(f"Note: {note}" for note in counts.get("notes") or [])
	return "\n".join(lines)


def _report(run, start, end, counts, errors, reason) -> None:
	"""ONE summary per run: to HR's notifications and onto the Error Log trail.

	The run id is in the title, so the Error Log row is the atomic key — a second
	attempt at the same run finds it and says nothing twice.
	"""
	title = f"{TITLE_PREFIX} {run}: {counts['days_rebuilt']} day(s) rebuilt, {counts['needs_hr']} need HR"
	try:
		if frappe.db.exists("Error Log", {"method": title}):
			logger.info("[attendance_endgame] %s already reported", run)
			return
	except Exception:
		logger.exception("[attendance_endgame] could not check for an earlier summary of %s", run)
	message = _message(run, start, end, counts, errors, reason)
	try:
		log = frappe.log_error(title=title, message=message)
		notify_hr(title, message, "Error Log", getattr(log, "name", None), company=None)
		frappe.db.commit()
	except Exception:
		logger.exception("[attendance_endgame] could not deliver the summary of %s", run)
	logger.info("[attendance_endgame] reported %s", title)


def _result(run, counts, errors, more, stopped_now, note=None) -> dict:
	return {
		"run": run,
		"counts": counts,
		"errors": errors,
		"more": more,
		"stopped": stopped_now,
		"note": note,
	}


# --- the orchestrator -----------------------------------------------------------------


def run_endgame(from_date=None, to_date=None, reason="deploy") -> dict:
	"""Do the whole repair, in order, resuming safely, and tell HR once.

	Never raises for anything the work itself can throw: a step that fails is
	recorded against its chunk and the run carries on, because one bad window
	must not starve the rest of the month. A worker KILL is not caught — nothing
	can be — but the marker written before each chunk means the next pass loses
	at most that chunk.
	"""
	global _CURRENT_RUN

	state = _load_state()
	if not state and not from_date and not to_date:
		try:
			if frappe.db.get_default(DONE_MARK):
				logger.info("[attendance_endgame] already completed; nothing to do")
				return _result(None, _counts(), [], False, False, note="already completed")
		except Exception:
			logger.exception("[attendance_endgame] could not read %s; running", DONE_MARK)

	start, end = _window(from_date, to_date)
	run = state.get("run") or _new_run_id()
	counts = _counts(state.get("counts"))
	errors = list(state.get("errors") or [])
	first_step = STEPS.index(state["step"]) if state.get("step") in STEPS else 0
	cursor = getdate(state["cursor"]) if state.get("cursor") else None
	done_this_pass = 0

	# Background jobs and the scheduler run as Administrator; say so, because the
	# writers underneath check System Manager rights.
	frappe.set_user("Administrator")
	_CURRENT_RUN = run
	logger.info("[attendance_endgame] run %s (%s) %s..%s", run, reason, start, end)
	try:
		for index in range(first_step, len(STEPS)):
			step = STEPS[index]
			begin, cursor = (cursor or start), None
			for chunk_start, chunk_end in _chunks(begin, end):
				if stopped():
					logger.warning("[attendance_endgame] %s halted at %s/%s", run, step, chunk_start)
					_save_state(run, step, chunk_start, counts, errors)
					return _result(run, counts, errors, True, True, note=f"halted by {STOP_SWITCH}")
				if done_this_pass >= MAX_CHUNKS_PER_PASS:
					logger.info(
						"[attendance_endgame] %s reached this pass's cap at %s/%s", run, step, chunk_start
					)
					_save_state(run, step, chunk_start, counts, errors)
					return _result(run, counts, errors, True, False, note="more to do next pass")
				_save_state(run, step, chunk_start, counts, errors)
				try:
					_RUNNERS[step](chunk_start, chunk_end, counts, errors)
					frappe.db.commit()
				except Exception as exc:
					frappe.db.rollback()
					logger.exception(
						"[attendance_endgame] %s %s..%s failed; moving on", step, chunk_start, chunk_end
					)
					errors.append(f"{step} {chunk_start}..{chunk_end}: {exc}")
				done_this_pass += 1
				logger.info("[attendance_endgame] %s %s %s..%s done", run, step, chunk_start, chunk_end)
		_report(run, start, end, counts, errors, reason)
		try:
			frappe.db.set_default(DONE_MARK, nowdate())
			# The nightly pass re-runs the whole window while no finished one-time
			# recovery is on record. This run did strictly more than that, so it
			# leaves the nightly's mark too — the two markers must not fight.
			frappe.db.set_default(auto.ONCE_MARK, nowdate())
			_clear_state()
			frappe.db.commit()
		except Exception:
			logger.exception("[attendance_endgame] could not record that %s finished", run)
		logger.info("[attendance_endgame] %s finished: %s", run, counts)
		return _result(run, counts, errors, False, False)
	finally:
		_CURRENT_RUN = None


def queue_endgame(reason="deploy") -> None:
	"""Enqueue the repair. The migrate NEVER does the work inline — a patch that
	repairs a month inside `bench migrate` holds the deploy open for hours and
	dies with it."""
	frappe.enqueue(
		"hrms.utils.attendance_endgame.run_endgame",
		queue="long",
		timeout=4 * 60 * 60,
		enqueue_after_commit=True,
		job_id=JOB_ID,
		deduplicate=True,
		reason=reason,
	)
	logger.info("[attendance_endgame] queued after %s", reason)


# --- undo -----------------------------------------------------------------------------


def _log_undo(entry, run_id) -> None:
	"""The undo leaves its own entry, pointing at the one it reversed."""
	doc = frappe.get_doc(
		{
			"doctype": rec.DAY_FIX_LOG,
			"source": "recovery",
			"run": f"{run_id}-undo",
			"employee": entry.get("employee"),
			"fix_date": str(entry.get("fix_date")),
			"action": "undo_run",
			"reason": f"reversed {entry.get('name')} of run {run_id}",
			"fixed_by": frappe.session.user,
			"before_state": entry.get("after_state"),
			"after_state": entry.get("before_state"),
			"undone": 0,
			"undo_of": entry.get("name"),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()


def _undo_entry(entry, run_id) -> dict:
	"""Put ONE day back the way the run found it, or say why that is refused."""
	name, employee, day = entry.get("name"), entry.get("employee"), entry.get("fix_date")
	base = {"entry": name, "employee": employee, "date": str(day)}

	if entry.get("run") != run_id:
		return {**base, "ok": False, "reason": "belongs to another run"}
	if cint(entry.get("undone")):
		return {**base, "ok": False, "reason": "already undone"}
	if entry.get("action") not in UNDOABLE:
		return {
			**base,
			"ok": False,
			"reason": f"nothing to reverse: a {entry.get('action')} entry changed no day",
		}
	try:
		before = json.loads(entry.get("before_state") or "{}")
	except Exception:
		before = {}
	if not before.get("name"):
		return {**base, "ok": False, "reason": "nothing was recorded to restore"}

	# The day may have moved on since the run touched it: a payout, an approval,
	# HR's own correction. Recovery's rule decides, exactly as it does going
	# forward — an undo must not walk over a decision made after the fix.
	held = rec._day_protection(employee, getdate(day), True)
	if held:
		logger.info("[attendance_endgame] %s on %s not put back: %s", employee, day, held)
		return {**base, "ok": False, "reason": held}

	frappe.db.savepoint(UNDO_SAVEPOINT)
	try:
		rec._lock_employee(employee)
		frappe.db.set_value(
			"Attendance",
			before["name"],
			{
				"status": before.get("status"),
				"working_hours": before.get("working_hours"),
				"in_time": before.get("in_time"),
				"out_time": before.get("out_time"),
			},
			update_modified=False,
		)
		frappe.db.set_value(
			rec.DAY_FIX_LOG,
			name,
			{"undone": 1, "undone_on": now_datetime(), "undone_by": frappe.session.user},
			update_modified=False,
		)
		_log_undo(entry, run_id)
		frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback(save_point=UNDO_SAVEPOINT)
		logger.exception("[attendance_endgame] %s could not be reversed", name)
		return {**base, "ok": False, "reason": f"could not be reversed: {exc}"}
	logger.info("[attendance_endgame] %s put %s back on %s", name, before["name"], day)
	return {**base, "ok": True, "attendance": before["name"]}


def undo_run(run_id) -> dict:
	"""Reverse every day this run rebuilt, newest first. Never raises.

	Only the entries carrying this `run` are read, and each one is checked again
	before it is touched: an entry already undone is refused, and so is a day
	that has since been paid, approved or corrected by HR — with the reason said
	per day, so nothing is reversed silently and nothing is reversed twice.
	"""
	restored, refused = [], []
	try:
		entries = frappe.get_all(
			rec.DAY_FIX_LOG,
			filters={"run": run_id},
			fields=["name", "run", "employee", "fix_date", "action", "undone", "before_state", "after_state"],
			order_by="creation desc",
			limit_page_length=0,
		)
	except Exception as exc:
		logger.exception("[attendance_endgame] could not read the entries of %s", run_id)
		return {"run": run_id, "restored": [], "refused": [], "note": str(exc)}

	for entry in entries or []:
		verdict = _undo_entry(entry, run_id)
		(restored if verdict.get("ok") else refused).append(verdict)
	logger.info("[attendance_endgame] undo %s: %d put back, %d refused", run_id, len(restored), len(refused))
	return {"run": run_id, "restored": restored, "refused": refused, "note": None}
