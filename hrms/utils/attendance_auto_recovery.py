"""Attendance recovery that runs itself — Nabil, 14 Sep 2026.

Nabil does not run console snippets: "why not let the system auto identify?"
and then "Fix automatically". Once after deploy (hrms/patches/v16_0/
run_attendance_recovery_once.py enqueues `run_once`) and every night
(`run_nightly`, last NIGHTLY_DAYS days), every recovery step of
hrms/utils/attendance_recovery.py is applied in its fixed order for the window
up to yesterday. The steps keep all their protections — never today, never an
HR-kept or HR-removed day, never leave / Attendance Request / half-day leave,
never a paid day — and hand what they cannot fix to hr_list.

The ERP `import` step is skipped: it needs the source instance over the
network, so it stays with the operator-run sync. The narrowed lone-IN closer
(`close_lone_ins`, S6) does run, insert-only with its own guards.

S7 (15 Sep 2026): a day older than the nightly window that breaks later (a late
approval, an HR hand-back) was never revisited. Every night, after the window,
the days the detectors (`attendance_recovery.unclaimable_rows`) list as
fixable are re-run as well — oldest first, at most RECHECK_CAP employee-days a
night, never today or yesterday. Each step has an off switch in HR Settings:
`attendance_recovery_skip_<step>` (and `..._skip_recheck`), a Check that reads
as ON (the step runs) while the field does not exist or is unticked — no
schema is added here; HR adds the field when a family must be paused.

HR gets one Desk notification (and one Error Log) per run day: per family,
fixed / on purpose / needs HR (E34), and how many days only HR can fix in
Shift Attendance. Never raises into the scheduler or a background job.
"""

import logging
from datetime import date, timedelta

import frappe
from frappe.utils import cint, getdate, nowdate
from frappe.utils.background_jobs import is_job_enqueued

from hrms.overrides.remote_checkin_request_hooks import notify_hr
from hrms.utils import attendance_recovery as rec

logger = logging.getLogger(__name__)

#: Every step in recovery's order except the ERP import (network, operator-run).
AUTO_STEPS = tuple(step for step in rec.STEPS if step != "import")
NIGHTLY_DAYS = 7
ONCE_JOB_ID = "attendance_recovery_once"
CHUNK_DAYS = 31
#: Flagged employee-days re-checked per night, oldest first (S7).
RECHECK_CAP = 200
#: HR Settings Check `attendance_recovery_skip_<name>`; absent or 0 = the step runs.
SWITCH_PREFIX = "attendance_recovery_skip_"
SWITCHED_OFF = "switched off in HR Settings"
#: The family (or families) each step fixes, for the HR summary (E34).
FAMILY_OF = {
	"release_mirrored": "ERP copies of broken days",
	"assignments": "F1 unused night assignment",
	"rostered_shift": "F1 taps on a shift the person is not rostered on",
	"overwritten": "F8 overwritten taps",
	"mirrored_rows": "mirrored Absent rows over hub taps",
	"close_lone_ins": "F3 lone IN closed by the ERP's OUT",
	"heal": "F11 shiftless taps",
	"skip_stamps": "F7 skipped taps",
	"rebuild": "F6/F9/F13 days the engine re-marks",
	"leftover_rows": "leftover rows on an ended shift",
	"ot_recount": "OT recount",
}

#: Reasons a day is left alone ON PURPOSE (hrms/utils/attendance_recovery.py
#: protected_reason, hrms/sync/checkin_import.py plan_remark, the OT recount).
#: Nothing for HR to fix: a leave, an HR-kept or HR-removed day, a paid day.
LEFT_ALONE_ON_PURPOSE = (
	"is a leave record",
	"is a half-day leave",
	"comes from an attendance request",
	"marked by hr by hand",
	"is marked by hand, a leave, or another instance's",
	"is a draft",
	"removed by hr",
	"hr removed this day",
	"depends on this day",
	"today or later",
)
TITLE_PREFIX = "Attendance recovery"
FAILURE_TITLE = "Attendance recovery run failed"


def needs_hr(held: dict) -> bool:
	"""A held-back day HR must correct: flagged for HR and not left alone on purpose."""
	reason = str(held.get("reason") or "").lower()
	return bool(held.get("hr")) and not any(phrase in reason for phrase in LEFT_ALONE_ON_PURPOSE)


def _yesterday() -> date:
	return getdate(nowdate()) - timedelta(days=1)


def _chunks(start: date, end: date):
	"""Windows of at most CHUNK_DAYS days, oldest first (recovery refuses > MAX_WINDOW_DAYS)."""
	while start <= end:
		stop = min(end, start + timedelta(days=CHUNK_DAYS - 1))
		yield start, stop
		start = stop + timedelta(days=1)


def switched_off(name: str) -> bool:
	"""HR Settings `attendance_recovery_skip_<name>`: 1 = paused. A field that does
	not exist yet, or is unticked, reads as ON — the step runs."""
	try:
		return bool(cint(frappe.get_single("HR Settings").get(SWITCH_PREFIX + name)))
	except Exception:
		logger.exception("[attendance_recovery_auto] could not read the %s switch; running it", name)
		return False


def _run(from_date, to_date) -> dict:
	"""Plan and apply every automatic step in order, per window; stop at the first failure.

	Calls recovery's planners and appliers directly — they carry every day
	protection. `apply_recovery`'s "earlier steps first" check would re-plan the
	ERP import (a network call) before each step; here the loop is the order.
	"""
	summary = {"from_date": str(from_date), "to_date": str(to_date), "steps": {}, "stopped_at": None}
	hr_days, protected_days = set(), set()
	paused = {step for step in AUTO_STEPS if switched_off(step)}
	for chunk_start, chunk_end in _chunks(getdate(from_date), getdate(to_date)):
		win = rec.recovery_window(chunk_start, chunk_end, getdate(nowdate()))
		for step in AUTO_STEPS:
			if step in paused:
				summary["steps"].setdefault(step, {"done": 0, "held_back": 0, "skipped": SWITCHED_OFF})
				logger.info("[attendance_recovery_auto] %s %s", step, SWITCHED_OFF)
				continue
			tally = summary["steps"].setdefault(
				step, {"done": 0, "held_back": 0, "needs_hr": 0, "on_purpose": 0}
			)
			try:
				plan = rec._PLANNERS[step](win, for_update=True)
				outcome = rec._APPLIERS[step](win, plan)
				frappe.db.commit()
			except Exception as exc:
				frappe.db.rollback()
				logger.exception("[attendance_recovery_auto] %s stopped the run at %s", step, win.start)
				tally["error"] = str(exc)[:300]
				summary["stopped_at"] = step
				summary["hr_days"] = len(hr_days)
				summary["protected_days"] = len(protected_days - hr_days)
				return summary
			held = (plan.get("held_back") or []) + (outcome.get("held_back") or [])
			tally["done"] += len(outcome.get("done") or [])
			tally["held_back"] += len(held)
			for h in held:
				if needs_hr(h):
					tally["needs_hr"] += 1
				else:
					tally["on_purpose"] += 1
				if not h.get("employee"):
					continue  # a step-level note (a tool not installed), not a day
				key = (h.get("employee"), str(h.get("date")))
				if needs_hr(h):
					hr_days.add(key)
				elif h.get("hr"):
					protected_days.add(key)
			logger.info("[attendance_recovery_auto] %s %s..%s: %s", step, win.start, win.end, tally)
		try:
			hr_days.update(
				(h.get("employee"), str(h.get("date"))) for h in rec._ot_request_review(win)["hr_list"]
			)
		except Exception:
			logger.exception("[attendance_recovery_auto] OT request review failed for %s", win.start)
	summary["hr_days"] = len(hr_days)
	summary["protected_days"] = len(protected_days - hr_days)
	return summary


def _merge(into: dict, part: dict) -> dict:
	"""One summary over several windows: counts add up, the first stop wins."""
	for step, tally in part["steps"].items():
		mine = into["steps"].setdefault(step, {"done": 0, "held_back": 0, "needs_hr": 0, "on_purpose": 0})
		for key in ("done", "held_back", "needs_hr", "on_purpose"):
			mine[key] = mine.get(key, 0) + tally.get(key, 0)
		if tally.get("skipped"):
			mine["skipped"] = tally["skipped"]
		if tally.get("error"):
			mine["error"] = tally["error"]
	into["hr_days"] = into.get("hr_days", 0) + part.get("hr_days", 0)
	into["protected_days"] = into.get("protected_days", 0) + part.get("protected_days", 0)
	into["stopped_at"] = into.get("stopped_at") or part.get("stopped_at")
	return into


def _family_lines(summary: dict) -> list:
	"""E34: one line per family — fixed / on purpose / needs HR."""
	lines = []
	for step in AUTO_STEPS:
		tally = summary["steps"].get(step)
		if not tally:
			continue
		label = f"{step} ({FAMILY_OF.get(step, step)})"
		if tally.get("skipped"):
			lines.append(f"{label}: {tally['skipped']}")
			continue
		lines.append(
			f"{label}: fixed {tally.get('done', 0)} · on purpose {tally.get('on_purpose', 0)} "
			f"· needs HR {tally.get('needs_hr', 0)}"
		)
	return lines


def _message(summary: dict) -> str:
	fixed = {step: s["done"] for step, s in summary["steps"].items() if s.get("done")}
	rechecked = summary.get("rechecked") or 0
	lines = [
		f"Window {summary['from_date']} → {summary['to_date']} (today is never touched)"
		+ (f", plus {rechecked} flagged day(s) re-checked." if rechecked else "."),
		f"Fixed: {sum(fixed.values())} change(s)"
		+ (" — " + ", ".join(f"{k} {v}" for k, v in fixed.items()) if fixed else ""),
		f"Days only HR can fix (open Shift Attendance): {summary.get('hr_days')}",
		f"Left alone on purpose (leave, HR-kept, paid): {summary.get('protected_days')}",
		"Per family:",
		*(f"  {line}" for line in _family_lines(summary)),
		"ERP punch import is not part of this run; it stays with the manual sync.",
	]
	if summary.get("stopped_at"):
		lines.append(
			f"Stopped at step {summary['stopped_at']}: {summary['steps'][summary['stopped_at']].get('error')}"
		)
	return "\n".join(lines)


def _report(summary: dict) -> None:
	day = nowdate()
	fixed = sum(s.get("done", 0) for s in summary["steps"].values())
	title = f"{TITLE_PREFIX} {day}: fixed {fixed}, {summary.get('hr_days')} day(s) need HR"
	if frappe.db.exists("Error Log", {"method": title}):
		logger.info("[attendance_recovery_auto] %s already reported", title)
		return
	message = _message(summary)
	log = frappe.log_error(title=title, message=message)
	notify_hr(title, message, "Error Log", getattr(log, "name", None), company=None)
	frappe.db.commit()
	logger.info("[attendance_recovery_auto] reported: %s", title)


def _safe(from_date, to_date, recheck: bool = False) -> dict | None:
	"""Run the window — and with `recheck`, every flagged day outside it (S7) —
	and report ONCE. Everything, the detector pass included, stays inside this
	one exception boundary: nothing raises into the scheduler."""
	try:
		# Background jobs and the scheduler run as Administrator; say so, since
		# recovery's writers check System Manager rights.
		frappe.set_user("Administrator")
		summary = _run(from_date, to_date)
		extra = (
			recheck_windows(flagged_days(getdate(to_date)), getdate(from_date), getdate(to_date))
			if recheck
			else []
		)
		rechecked = 0
		for start, end in extra:
			if summary.get("stopped_at"):
				break
			summary = _merge(summary, _run(start, end))
			rechecked += (end - start).days + 1
		summary["rechecked"] = rechecked
		_report(summary)
		return summary
	except Exception:
		logger.exception("[attendance_recovery_auto] run crashed")
		try:
			frappe.log_error(title=FAILURE_TITLE, message=frappe.get_traceback())
		except Exception:
			logger.exception("[attendance_recovery_auto] could not even log the crash")
		return None


def run_once() -> dict | None:
	"""After deploy: 1 August (recovery's floor) to yesterday."""
	logger.info("[attendance_recovery_auto] one-time run %s..%s", rec.REPAIR_FLOOR, _yesterday())
	return _safe(rec.REPAIR_FLOOR, _yesterday())


def run_nightly() -> dict | None:
	"""Scheduler entry: NIGHTLY_DAYS days ending the day before yesterday.

	Daily jobs fire just after midnight, while yesterday's night shift
	(19:30-03:30) still has only its IN — so yesterday waits one more night.
	Skips while the one-time run is still queued or running.
	"""
	if is_job_enqueued(ONCE_JOB_ID):
		logger.info("[attendance_recovery_auto] one-time run still going; nightly skipped")
		return None
	end = _yesterday() - timedelta(days=1)
	start = max(rec.REPAIR_FLOOR, end - timedelta(days=NIGHTLY_DAYS - 1))
	logger.info("[attendance_recovery_auto] nightly run %s..%s", start, end)
	return _safe(start, end, recheck=not switched_off("recheck"))


def flagged_days(end: date) -> list:
	"""(employee, day) the detectors list as fixable between the floor and `end`,
	oldest first, at most RECHECK_CAP (S7). One detector pass per chunk."""
	found = set()
	if end < rec.REPAIR_FLOOR:
		return []
	for start, stop in _chunks(rec.REPAIR_FLOOR, end):
		win = rec.recovery_window(start, stop, getdate(nowdate()))
		for row in rec.unclaimable_rows(win):
			# only a day one of the nightly steps can act on (F4 is listed, not fixed)
			if row.get("status") != rec.STATUS_FIXABLE or row.get("fix") not in AUTO_STEPS:
				continue
			if row.get("employee") and row.get("date"):
				found.add((row["employee"], getdate(row["date"])))
	days = sorted(found, key=lambda d: (d[1], str(d[0])))[:RECHECK_CAP]
	logger.info("[attendance_recovery_auto] %d flagged day(s) to re-check (of %d)", len(days), len(found))
	return days


def recheck_windows(days, skip_start: date, skip_end: date) -> list:
	"""Date ranges covering `days`, consecutive dates merged, minus the window
	already run. Pure."""
	dates = sorted({d for _e, d in days if not (skip_start <= d <= skip_end)})
	windows = []
	for day in dates:
		if windows and windows[-1][1] + timedelta(days=1) == day:
			windows[-1] = (windows[-1][0], day)
		else:
			windows.append((day, day))
	return windows
