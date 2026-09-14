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
network, so it stays with the operator-run sync.

HR gets one Desk notification (and one Error Log) per run day with what was
fixed and how many days only HR can fix in Shift Attendance. Never raises into
the scheduler or a background job.
"""

import logging
from datetime import date, timedelta

import frappe
from frappe.utils import getdate, nowdate
from frappe.utils.background_jobs import is_job_enqueued

from hrms.overrides.remote_checkin_request_hooks import notify_hr
from hrms.utils import attendance_recovery as rec

logger = logging.getLogger(__name__)

#: Every step in recovery's order except the ERP import (network, operator-run).
AUTO_STEPS = tuple(step for step in rec.STEPS if step != "import")
NIGHTLY_DAYS = 7
ONCE_JOB_ID = "attendance_recovery_once"
CHUNK_DAYS = 31

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


def _run(from_date, to_date) -> dict:
	"""Plan and apply every automatic step in order, per window; stop at the first failure.

	Calls recovery's planners and appliers directly — they carry every day
	protection. `apply_recovery`'s "earlier steps first" check would re-plan the
	ERP import (a network call) before each step; here the loop is the order.
	"""
	summary = {"from_date": str(from_date), "to_date": str(to_date), "steps": {}, "stopped_at": None}
	hr_days, protected_days = set(), set()
	for chunk_start, chunk_end in _chunks(getdate(from_date), getdate(to_date)):
		win = rec.recovery_window(chunk_start, chunk_end, getdate(nowdate()))
		for step in AUTO_STEPS:
			tally = summary["steps"].setdefault(step, {"done": 0, "held_back": 0})
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


def _message(summary: dict) -> str:
	fixed = {step: s["done"] for step, s in summary["steps"].items() if s.get("done")}
	lines = [
		f"Window {summary['from_date']} → {summary['to_date']} (today is never touched).",
		f"Fixed: {sum(fixed.values())} change(s)"
		+ (" — " + ", ".join(f"{k} {v}" for k, v in fixed.items()) if fixed else ""),
		f"Days only HR can fix (open Shift Attendance): {summary.get('hr_days')}",
		f"Left alone on purpose (leave, HR-kept, paid): {summary.get('protected_days')}",
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


def _safe(from_date, to_date) -> dict | None:
	try:
		# Background jobs and the scheduler run as Administrator; say so, since
		# recovery's writers check System Manager rights.
		frappe.set_user("Administrator")
		summary = _run(from_date, to_date)
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
	return _safe(start, end)
