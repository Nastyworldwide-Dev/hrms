"""HR Fix Days — Fix Day's one press, over a date range.

Owner's case, 21 Sep 2026 (screenshots): Norazmi's 1-4 September. Every punch
had been corrected by hand — one IN and one OUT a day, all Counted, all on
8AM-6PM — and the Attendance list still read "Absent (HR)" 0.00 h on each,
beside the cancelled night rows and one Half Day 0.01 h from a double tap under
the night stamp. On 3 September the IN still carried 7PM-3.30AM while its OUT
was on 8AM-6PM. Punches fixed, attendance never recomputed, glitch stamps mixed.

For EACH day of the range, in order, with the person locked for the whole call:

1. RE-STAMP. `shift` given: every local punch of that day's SESSION (the engine's
   IN-anchored rule, `attendance_recovery.session_days`) gets the
   whole stamp of `shift` on that day (`_shift_stamp`) and is released from
   its row; a punch already on it is left alone. `shift` None: the roster
   decides, through `restamp`'s own resolution (`_roster_stamp`).
2. PAIR + NOISE. `day_plan` on the re-stamped taps: first IN opens, last OUT
   closes, everything between is noise. No complete session → the day is
   reported "left open" and NOTHING on it is written — no Absent invented.
3. CANCEL. Every submitted row on the day that `release_to_automation` would
   hand back — INCLUDING HR's own `auto_attendance = 0` rows, because HR is
   asking — and any extra row, and a row an Attendance Request wrote. Leave,
   half-day leave, On Leave and mirrored rows are never cancelled; such a day
   is refused whole by `_day_block`, as is a paid day, a future day and a
   running shift. The refusal is per day; the other days proceed.
   REQUESTS STAY INTACT (owner ruling, 21 Sep 2026): a day under an approved
   OT Request, Attendance Request or Compensatory Leave Request is rebuilt
   like any other and the request document is never touched — no cancel, no
   edit. The answer lists them per day as `requests_kept`; OT hours on the
   row are recomputed from the punches and the request keeps its approval.
   The one line not crossed is money already paid: a submitted salary slip
   covering the day, or overtime already on one — refused and named.
4. REBUILD. `_rebuild` — the one engine, `hr_asked`, inline — one row.
5. LOG. One HR Day Fix Log row per day, action `fix_days`, the touched taps
   snapshotted so `undo_fix` puts their stamps back.

Nothing here types a status or an hour (pinned by test_fix_days.py). The
per-day primitives stay in `attendance_fix_day`; this module is the loop and
the shape of the answer. The Desk dialog is the next slice.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hrms.api import attendance_fix_day as fd
from hrms.utils.attendance_recovery import session_days

logger = logging.getLogger(__name__)

ACTION = "fix_days"
#: one pay window and a bit; a longer range is two presses
MAX_DAYS = 31
STAMP_FIELDS = ("shift", "shift_start", "shift_end", "shift_actual_start", "shift_actual_end", "offshift")
#: what "already on that stamp" compares — `restamp.COMPARED_FIELDS`
COMPARED_FIELDS = ("shift", "shift_start", "shift_end", "offshift")


# --- pure rules ------------------------------------------------------------------


def keeps_the_day(row) -> bool:
	"""Whether this row speaks for the day and is never cancelled here. Pure.

	The list `attendance_recovery.release_to_automation` keeps its hands off —
	a leave, a half-day leave, On Leave, a Leave Application, a mirrored row,
	anything not submitted — EXCEPT a row from an Attendance Request: that row
	is rebuilt from the punches here while the request keeps its approval
	(owner ruling, 21 Sep 2026).
	"""
	return bool(
		cint(row.get("docstatus")) != 1
		or row.get("leave_type")
		or row.get("leave_application")
		or row.get("synced_from_instance")
		or cint(row.get("modify_half_day_status"))
		or row.get("status") == "On Leave"
	)


def rows_to_cancel(rows) -> list:
	"""The day's live rows that go before the rebuild, HR-owned ones included. Pure."""
	return [row for row in rows or [] if not keeps_the_day(row)]


def same_stamp(tap, stamp) -> bool:
	"""Whether the tap already carries this stamp. Pure."""
	return all(str(tap.get(f) or "") == str(stamp.get(f) or "") for f in COMPARED_FIELDS)


def stamp_view(source) -> dict:
	return {
		"shift": source.get("shift"),
		"shift_start": str(source.get("shift_start")) if source.get("shift_start") else None,
	}


def day_of(tap, stamp=None):
	"""The shift day a tap belongs to under a stamp: the IN's day rule. Pure."""
	return getdate((stamp or tap).get("shift_start") or tap.get("time"))


# --- the action --------------------------------------------------------------------


def fix_days(employee, from_date, to_date, shift=None, reason="", dry_run=True) -> dict:
	"""See the module docstring. Whitelisted through `attendance_fix_day.fix_days`."""
	fd._require_hr()
	dry_run = _truthy(dry_run)
	reason = (reason or "").strip() if dry_run else fd._require_reason(reason)
	emp = fd._require_employee(employee)
	days = _days(from_date, to_date)
	fd._lock_employee(emp.name)
	taps = fd._range_taps(emp.name, days[0], days[-1])
	assigned = _assign(taps, shift, days)
	logger.info(
		"[attendance_fix_days] %s %s..%s on %s by %s: %d tap(s), %s",
		emp.name,
		days[0],
		days[-1],
		shift or "the roster",
		frappe.session.user,
		len(taps),
		"dry run" if dry_run else "applying",
	)
	report = [_fix_one_day(emp, day, shift, assigned.get(day, []), reason, dry_run) for day in days]
	return {
		"ok": True,
		"dry_run": dry_run,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"from_date": str(days[0]),
		"to_date": str(days[-1]),
		"shift": shift or None,
		"days": report,
		"totals": _totals(report),
	}


def _fix_one_day(emp, day, shift, taps, reason, dry_run) -> dict:
	"""One day, start to finish. `taps` are (tap, new_stamp | None) pairs assigned
	to this day: None means the tap already carries the stamp."""
	rows = fd._day_attendance(emp.name, day)
	# The day guard first, and per day: a refused day is reported, not raised —
	# the person pressed once for the whole range. `duplicate_rows_ok`: a
	# two-row day is exactly what this ends.
	blocked = fd._day_block(
		emp.name, day, rows, for_update=not dry_run, duplicate_rows_ok=True, requests_ok=True
	)
	entry = {
		"date": str(day),
		"blocked": blocked,
		"taps": [_tap_change(tap, new) for tap, new in taps],
		"rows_to_cancel": [] if blocked else [_row_brief(row) for row in rows_to_cancel(rows)],
		# read on a refused day too: HR sees what the day carries either way
		"requests_kept": [request_kept(req) for req in fd._requests_on(emp.name, day)],
		"noise": [],
		"session": None,
		"result": None,
		"log": None,
		"rebuild": None,
	}
	if blocked:
		entry["result"] = _("refused: {0}").format(blocked)
		logger.info("[attendance_fix_days] %s on %s refused: %s", emp.name, day, blocked)
		return entry

	if not taps:
		# Not "left open": nothing punched on this day (or its punches belong to
		# another day's session). Nothing to read, nothing to write.
		entry["result"] = _("no punches on this day")
		entry["rows_to_cancel"] = []
		return entry
	# The plan is read from the taps AS THEY WILL BE, in memory, dry run or not.
	after = [{**tap, **(new or {})} for tap, new in taps]
	remaining = [row for row in rows if keeps_the_day(row)]
	plan = fd.day_plan(after, remaining, pairing=fd._day_pairing(after))
	if plan["refusal"]:
		# No session: nothing is written, not even the stamps. Writing half a
		# day and leaving the row behind is how a day reads Absent for ever.
		entry["result"] = _("left open: {0}").format(plan["refusal"])
		entry["rows_to_cancel"] = []
		return entry
	entry["noise"] = plan["drop"]
	entry["session"] = plan["session"]
	entry["result"] = _("will rebuild from {0} to {1}").format(
		fd.fd_clock_text(plan["session"]["in"]["time"]), fd.fd_clock_text(plan["session"]["out"]["time"])
	)
	if dry_run:
		return entry
	return _apply(emp, day, shift, taps, plan, rows, reason, entry)


def _apply(emp, day, shift, taps, plan, rows, reason, entry) -> dict:
	"""Write what the plan says, rebuild through the one engine, log the day."""
	by_name = {tap["name"]: tap for tap, _new in taps}
	before = fd._before(emp.name, [day], list(by_name.values()))
	cancel = [
		{
			"name": row["name"],
			"shift": row.get("shift"),
			"status": row.get("status"),
			"why": _("rebuilt from its punches"),
		}
		for row in rows_to_cancel(rows)
	]
	logger.warning(
		"[attendance_fix_days] %s on %s by %s: cancel %s, re-stamp %s, drop %s",
		emp.name,
		day,
		frappe.session.user,
		[row["name"] for row in cancel],
		[tap["name"] for tap, new in taps if new],
		[drop["name"] for drop in plan["drop"]],
	)
	for row in cancel:
		fd._cancel_attendance(row["name"])
		fd._comment(
			"Attendance",
			row["name"],
			_("cancelled by Fix Days ({0}) by {1}. Reason: {2}").format(
				row["why"], frappe.session.user, reason
			),
		)
	notes = {}
	for tap, new in taps:
		if new:
			# released from its row for the same reason `move_tap` releases one
			fd._write_tap(tap, {**new, "attendance": None})
			tap.update(new)
			notes[tap["name"]] = _("re-stamped to {0} on {1} by Fix Days").format(new.get("shift"), day)
			if tap.get("_left"):
				fd._remark_later(emp.name, tap["_left"], f"fix days: {tap['name']} left the day")
	for drop in plan["drop"]:
		tap = by_name[drop["name"]]
		if not cint(tap.get("skip_auto_attendance")) or not cint(tap.get("skipped_as_noise")):
			fd._write_tap(tap, {"skip_auto_attendance": 1, "skipped_as_noise": 1})
		notes[drop["name"]] = _("ignored by Fix Days: {0}").format(drop["why"])
	opening, closing = by_name[plan["session"]["in"]["name"]], by_name[plan["session"]["out"]["name"]]
	wanted = {r["name"]: r["to"] for r in plan["relabel"]}
	fd._write_tap(
		opening,
		{
			"skip_auto_attendance": 0,
			"attendance": None,
			**({"log_type": wanted[opening["name"]]} if opening["name"] in wanted else {}),
		},
		relabelling=opening["name"] in wanted,
	)
	fd._write_tap(
		closing,
		{
			**fd._session_stamp(opening),
			"skip_auto_attendance": 0,
			"attendance": None,
			**({"log_type": wanted[closing["name"]]} if closing["name"] in wanted else {}),
		},
		relabelling=closing["name"] in wanted,
	)
	session_note = _("kept by Fix Days as this day's session")
	notes.setdefault(opening["name"], session_note)
	notes.setdefault(closing["name"], session_note)
	for name, note in notes.items():
		fd._comment(
			"Employee Checkin", name, _("{0} by {1}. Reason: {2}").format(note, frappe.session.user, reason)
		)

	rebuild = fd._rebuild(emp.name, day, f"fix days: {reason}", requests_ok=True)
	if why := fd.not_applied(rebuild):
		# The Release 1 rule: a fix the engine did not apply is never logged as
		# done — including one it ran and marked no row for (25 Sep 2026).
		# Raising rolls the whole request back and HR sees why.
		frappe.throw(_("{0} was not rebuilt, so nothing was changed: {1}").format(day, why))
	after_rows = fd._day_attendance(emp.name, day)
	entry["log"] = fd._write_log(
		{
			"employee": emp.name,
			"fix_date": str(day),
			"action": ACTION,
			"source": fd.LOG_SOURCE,
			"refs": ", ".join(sorted(notes)),
			"reason": reason,
			"fixed_by": frappe.session.user,
			"before_state": _json(before),
			"after_state": _json(
				{
					"days": {str(day): [fd.row_view(row) for row in after_rows]},
					"plan": {
						**plan,
						"cancel": cancel,
						"shift": shift,
						"restamped": [t["name"] for t, n in taps if n],
						"requests_kept": entry["requests_kept"],
					},
				}
			),
			"rebuild": _json({str(day): rebuild}),
		}
	)
	entry["rebuild"] = rebuild
	entry["result"] = _result(after_rows, rebuild)
	logger.info("[attendance_fix_days] %s on %s: %s (log %s)", emp.name, day, entry["result"], entry["log"])
	return entry


# --- shaping -----------------------------------------------------------------------


def _assign(taps, shift, days) -> dict:
	"""{day: [(tap, new_stamp | None)]}: which day each tap is fixed under, and the
	stamp it should carry there. Only days in the range are kept."""
	wanted = set(days)
	stamps = {}

	def stamp_for(day):
		if day not in stamps:
			stamps[day] = fd._shift_stamp(shift, day)
		return stamps[day]

	# The engine's IN-anchored session rule, not the clock: an IN opens a session
	# on its own day and every punch within the session window belongs to that
	# day whatever the clock says (a night OUT the next morning is not the next
	# day's). `session_days` is the recovery's own walk of exactly that rule.
	anchors = session_days(taps) if shift else {}
	out = {}
	for tap in taps:
		if shift:
			day = getdate(anchors[tap["name"]])
			new = stamp_for(day)
		else:
			new = fd._roster_stamp(tap) or {f: tap.get(f) for f in STAMP_FIELDS}
			day = day_of(tap, new)
			# the day it LEAVES, when that day is outside the range: nothing here
			# rebuilds it, so it is queued for the engine, as `restamp` queues it
			if day_of(tap) != day and day_of(tap) not in wanted:
				tap["_left"] = day_of(tap)
		if day in wanted:
			out.setdefault(day, []).append((tap, None if same_stamp(tap, new) else dict(new)))
	return out


def _tap_change(tap, new) -> dict:
	return {
		"name": tap["name"],
		"time": str(tap.get("time")),
		"log_type": tap.get("log_type"),
		"before": stamp_view(tap),
		"after": stamp_view(new or tap),
		"changed": bool(new),
	}


def request_kept(req) -> dict:
	"""How a kept request reads on the screen and in the log. Pure."""
	hours = f" {req['hours']} h" if req.get("hours") else ""
	label = f"{req['doctype']} {req['name']}{hours} ({req.get('status') or 'Approved'})"
	if req["doctype"] == "OT Request":
		label += " — " + _(
			"OT hours on the row are recomputed from the punches; the request keeps its approval"
		)
	return {"doctype": req["doctype"], "name": req["name"], "label": label}


def _row_brief(row) -> dict:
	"""Read through the screen's own row view: hours are read here, never written."""
	view = fd.row_view(row)
	return {key: view[key] for key in ("name", "status", "hours", "marked_by_hr")}


def _result(rows, rebuild) -> str:
	live = [fd.row_view(row) for row in rows if cint(row.get("docstatus")) == 1]
	if not live:
		return _("no row: {0}").format(rebuild.get("detail") or rebuild.get("action"))
	return " / ".join(f"{row['status']} {row['hours']} h" for row in live)


def _totals(report) -> dict:
	return {
		"days": len(report),
		"rebuilt": sum(1 for e in report if e["session"] and not e["blocked"]),
		"open": sum(1 for e in report if e["taps"] and not e["blocked"] and not e["session"]),
		"empty": sum(1 for e in report if not e["taps"] and not e["blocked"]),
		"blocked": sum(1 for e in report if e["blocked"]),
		"restamped": sum(1 for e in report if e["session"] for t in e["taps"] if t["changed"]),
		"noise": sum(len(e["noise"]) for e in report),
		"cancelled": sum(len(e["rows_to_cancel"]) for e in report),
		"kept": sum(len(e["requests_kept"]) for e in report),
	}


def _days(from_date, to_date) -> list:
	start, end = getdate(from_date), getdate(to_date)
	if end < start:
		fd._refuse(_("The end of the range is before its start."))
	if (end - start).days + 1 > MAX_DAYS:
		fd._refuse(_("Fix at most {0} days in one press.").format(MAX_DAYS))
	return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def _truthy(value) -> bool:
	"""A form posts "0"/"false" for a cleared tick; `bool("0")` would read it as set."""
	return str(value).strip().lower() not in ("0", "false", "no", "", "none")


def _json(value) -> str:
	return json.dumps(value, default=str, indent=1)
