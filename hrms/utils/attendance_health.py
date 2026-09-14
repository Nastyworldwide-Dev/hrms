"""Daily attendance health check: warn HR before staff complaints do.

`attendance_recovery.inputs_report` already answers "what is wrong with the
engine's inputs right now?" — this module is the daily nag on top of it: run
that same read, and when it is not all-clear, put ONE Error Log (plus a Desk alert for HR) in front of HR
instead of waiting for a staff complaint to surface a broken day.

Two entry points, same shape as `hrms.utils.readiness`:

  `run_daily_health_check`  the scheduler job. Read-only, never raises.
  `health_summary`          whitelisted GET, for a future Desk card.

Both read yesterday only, plus a rolling trailing window — never today
(`attendance_recovery.REPAIR_FLOOR`/`recovery_window` already refuse anything
else; this module never even asks).

`health_summary` is opened to HR User as well as HR Manager / System Manager
(the owner's ask), but `inputs_report` itself is gated System Manager / HR
Manager only (`_require_operator`), so a plain HR User calling it directly
would be refused by that INNER gate even after clearing this module's own
OUTER one. Re-authenticating as a different user just to read a report would
be a session mutation inside a GET — its own footgun. Instead, `_sections()`
below calls the exact same private planners `inputs_report` calls for its six
FIX-bearing sections (`_plan_assignments`, `_plan_heal`, `_plan_skip_stamps`,
`_plan_mirrored_rows`, `_late_checkouts`, `_plan_overwritten`), through the
same `_section()` formatter `inputs_report` itself uses. Nothing here
re-derives what those functions compute — it is the identical read, just
without the second, narrower role gate. `run_daily_health_check` still calls
`inputs_report` directly (it runs as Administrator on the scheduler, which
`only_for` always lets through), so the two entry points can never disagree
about the fix-bearing sections — they call the same underlying planners
either way. The two sections `_sections()` leaves out are the ones that
never bear on "is a day broken": `f_missing_erp_punches` needs
`include_source=1` (a live remote read this health check never makes) and
`h_days_after_today` is a "today is excluded" notice, never a fix.
"""

import logging
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms.overrides.company_scope import require_unfenced
from hrms.overrides.remote_checkin_request_hooks import notify_hr
from hrms.utils import attendance_recovery as rec
from hrms.utils.offshift_punch_heal import _lost_transaction

logger = logging.getLogger(__name__)

TITLE_PREFIX = "Attendance health"
FAILURE_TITLE = "Attendance health check failed"
#: how many days the rolling summary covers, yesterday included
TREND_DAYS = 7
#: up to this many employee/date lines per section in the Error Log body
SAMPLE = 10
#: health_summary's rolling window is clamped to this many days (recovery's MAX_WINDOW_DAYS)
MAX_SUMMARY_DAYS = 62

#: (section name, recovery step, planner) — the same six FIX-bearing reads
#: `inputs_report` makes. See the module docstring for why `health_summary`
#: calls these directly instead of `inputs_report` itself.
_SECTION_STEPS = (
	# The planner is named, not bound, and looked up on `rec` at call time
	# (`getattr`) rather than captured here — a module-level bound reference
	# would freeze the original function in this tuple forever, so a test (or
	# anything else) patching `attendance_recovery._plan_heal` would silently
	# not apply to this module.
	("a_wrong_night_assignment", "assignments", "_plan_assignments"),
	("b_shiftless_punches", "heal", "_plan_heal"),
	("c_skip_stamped_punches", "skip_stamps", "_plan_skip_stamps"),
	("d_mirrored_absent_rows", "mirrored_rows", "_plan_mirrored_rows"),
	("e_late_checkout_still_broken", "rebuild", "_late_checkouts"),
	("g_overwritten_punches", "overwritten", "_plan_overwritten"),
)


def _today() -> date:
	return getdate(now_datetime())


def _yesterday() -> date:
	return _today() - timedelta(days=1)


def _sections(win) -> dict:
	"""The same six fix-bearing sections `inputs_report` reads, for one window."""
	sections = {}
	for name, fix, plan_attr in _SECTION_STEPS:
		try:
			sections[name] = rec._section(fix, getattr(rec, plan_attr)(win))
		except Exception as exc:
			if _lost_transaction(exc):
				raise
			logger.exception("[attendance_health] section %s failed", name)
			sections[name] = {"error": str(exc)}
	return sections


def _broken(sections: dict) -> dict:
	"""{name: section} for every section carrying real fix work, or one that
	could not even be read (an unread section is unknown, not clean)."""
	broken = {}
	for name, section in (sections or {}).items():
		if not isinstance(section, dict):
			continue
		if section.get("error"):
			broken[name] = section
		elif section.get("fix") and section.get("count"):
			broken[name] = section
	return broken


def _count(section: dict) -> int:
	return 1 if section.get("error") else cint(section.get("count"))


def _lines(name: str, section: dict) -> list:
	if section.get("error"):
		return [f"{name}: could not be read ({section['error']})"]
	lines = [f"{name}: {section.get('count')} (recovery step: {section.get('fix')})"]
	for row in (section.get("sample") or [])[:SAMPLE]:
		lines.append(f"  - {row.get('employee')} {row.get('date')}")
	return lines


def _message(day, daily_broken: dict, trend_broken: dict, trend_from, trend_to) -> str:
	parts = [f"Yesterday ({day}):"]
	if daily_broken:
		for name in sorted(daily_broken):
			parts += _lines(name, daily_broken[name])
	else:
		parts.append("  nothing broken yesterday on its own")
	parts.append("")
	parts.append(f"Rolling {TREND_DAYS}-day check ({trend_from} to {trend_to}):")
	if trend_broken:
		for name in sorted(trend_broken):
			parts += _lines(name, trend_broken[name])
	else:
		parts.append("  nothing broken in the trailing week")
	return "\n".join(parts)


def _write_log(day, daily: dict, trend: dict) -> None:
	daily_broken = _broken(daily.get("sections"))
	trend_broken = _broken(trend.get("sections"))
	if not daily_broken and not trend_broken:
		logger.info("[attendance_health] %s: nothing broken", day)
		return
	total = sum(_count(s) for s in daily_broken.values()) or sum(_count(s) for s in trend_broken.values())
	title = f"{TITLE_PREFIX}: {total} broken day(s) on {day}"
	if frappe.db.exists("Error Log", {"method": title}):
		logger.info("[attendance_health] %s already logged, not duplicating", title)
		return
	message = _message(day, daily_broken, trend_broken, trend.get("from_date"), trend.get("to_date"))
	log = frappe.log_error(title=title, message=message)
	logger.warning("[attendance_health] %s", title)
	# Error Log is System Manager only; HR sees the alert in Desk (W6). The body
	# spans every company, so only unfenced HR gets it (company=None).
	notify_hr(title, message, "Error Log", getattr(log, "name", None), company=None)


def _run_daily_health_check() -> None:
	yesterday = _yesterday()
	trend_start = yesterday - timedelta(days=TREND_DAYS - 1)
	# ceiling: exactly two inputs_report calls per run (yesterday, and the
	# trailing TREND_DAYS window) — never a call per employee or per day;
	# upgrade: page the trend window if TREND_DAYS ever needs to grow past
	# what one inputs_report call can plan without timing out.
	daily = rec.inputs_report(from_date=str(yesterday), to_date=str(yesterday), include_source=0)
	trend = rec.inputs_report(from_date=str(trend_start), to_date=str(yesterday), include_source=0)
	_write_log(yesterday, daily, trend)


def run_daily_health_check() -> None:
	"""Scheduler entry. Read-only, and must never raise into the scheduler —
	a health check that can crash the scheduler is worse than none."""
	try:
		_run_daily_health_check()
	except Exception:
		logger.exception("[attendance_health] health check crashed")
		try:
			frappe.log_error(title=FAILURE_TITLE, message=frappe.get_traceback())
		except Exception:
			logger.exception("[attendance_health] could not even log the crash")


@frappe.whitelist(methods=["GET"])
def health_summary(days=7) -> dict:
	"""Read-only summary for yesterday plus a rolling window.

	Same read `run_daily_health_check` makes (see the module docstring for why
	this does not call `inputs_report` directly), safe for HR User too.
	"""
	frappe.only_for(("System Manager", "HR Manager", "HR User"))
	require_unfenced(_("read attendance health across every company"))
	days = min(max(cint(days) or TREND_DAYS, 1), MAX_SUMMARY_DAYS)
	today = _today()
	yesterday = today - timedelta(days=1)
	trend_start = yesterday - timedelta(days=days - 1)
	daily_win = rec.recovery_window(str(yesterday), str(yesterday), today)
	trend_win = rec.recovery_window(str(trend_start), str(yesterday), today)
	return {
		"date": str(yesterday),
		"daily": {
			"from_date": str(daily_win.start),
			"to_date": str(daily_win.end),
			"sections": _sections(daily_win),
		},
		"trend": {
			"from_date": str(trend_win.start),
			"to_date": str(trend_win.end),
			"sections": _sections(trend_win),
		},
	}
