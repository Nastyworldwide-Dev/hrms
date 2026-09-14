"""Put 1 August 2026 to yesterday right by fixing what the attendance engine READS.

Two earlier repair reports were refuted for pairing punches themselves: live
shifts use "Alternating entries" (first log to last log inside the shift
window), so any second pairing model drifts from the engine and invents fixes.
This module pairs nothing and computes no hours. It lists wrong INPUTS, each
with the existing tool that fixes it, runs those tools one step at a time, and
then lets the engine's own day rebuild (`checkin_import._remark_day`, the
rule `remark_attendance` uses) re-mark the day.

Steps, in this order — a later step refuses to write while an earlier one
still has planned work (System Manager may `force=1`):

1. assignments   end a night assignment a day worker never used (Ria)
2. overwritten   checkin_recovery.recover_overwritten_checkins (August overwrite)
3. mirrored_rows cancel automation-owned mirrored Absent rows over hub punches
4. import        checkin_import.import_missing_checkins (source-only punches)
5. heal          offshift_punch_heal (shiftless punches, not_before 1 Aug)
6. skip_stamps   attendance_day_audit.repair_attendance_days
7. rebuild       the engine re-marks each unread day
8. ot_recount    attendance.recompute_ot_backfill

Owner rulings (14 Sep 2026) held in every step: today and later are never
touched; HR hand-marked, leave, half-day-leave and Attendance Request rows are
never rebuilt; a day tied to an approved OT Request, submitted Salary Slip or
Overtime Details is left alone (`_repair_financial_dependency`); nobody is
asked — what cannot be fixed goes to `hr_list`.

Mirrored release path: `Attendance.cancel()` through the document, so the
write-block hook (`hrms.sync.write_block.block_mirrored_writes`, before_cancel)
judges it — allowed once the instance is unlocked at cutover, otherwise only a
System Manager break-glass (logged to Error Log); anything else is refused and
that row is held back. `Attendance.on_cancel` unlinks its punches, which the
rebuild step then reads.
"""

import logging
from collections import Counter, namedtuple
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from hrms.overrides.company_scope import require_unfenced
from hrms.utils.dry_run import wants_dry_run
from hrms.utils.offshift_punch_heal import _lost_transaction

logger = logging.getLogger(__name__)

#: Owner ruling: OT stays claimable four cycles back, so repair starts here.
REPAIR_FLOOR = date(2026, 8, 1)
#: unlock_mirrored_writes day. Before it the source ERP owned attendance.
CUTOVER = date(2026, 9, 4)
MAX_WINDOW_DAYS = 62
STEPS = (
	"assignments",
	"overwritten",
	"mirrored_rows",
	"import",
	"heal",
	"skip_stamps",
	"rebuild",
	"leftover_rows",
	"ot_recount",
)
#: The modules behind these refuse anyone but a System Manager.
SYSTEM_MANAGER_STEPS = ("overwritten", "skip_stamps")
NIGHT_START_MIN = 18 * 60
NIGHT_END_MAX = 6 * 60
ROW_SAVEPOINT = "attendance_recovery_row"
SAMPLE = 10
ATTENDANCE_FIELDS = [
	"name",
	"employee",
	"attendance_date",
	"status",
	"docstatus",
	"auto_attendance",
	"leave_type",
	"leave_application",
	"attendance_request",
	"modify_half_day_status",
	"synced_from_instance",
	"working_hours",
	"out_time",
]

Window = namedtuple("Window", "start end excluded_from requested_end")


# --- pure -----------------------------------------------------------------------


def recovery_window(from_date, to_date, today: date) -> Window:
	"""[start, end] inclusive: never before REPAIR_FLOOR, never after yesterday. Pure."""
	yesterday = today - timedelta(days=1)
	start = max(getdate(from_date), REPAIR_FLOOR) if from_date else REPAIR_FLOOR
	requested_end = getdate(to_date) if to_date else yesterday
	end = min(requested_end, yesterday)
	if start > end:
		raise ValueError(f"nothing to repair between {start} and {end}: today and later are never touched")
	if (end - start).days + 1 > MAX_WINDOW_DAYS:
		raise ValueError(f"{(end - start).days + 1} days; repair at most {MAX_WINDOW_DAYS} days per run")
	excluded = today if requested_end >= today else None
	logger.debug("[attendance_recovery] window %s..%s (asked to %s)", start, end, requested_end)
	return Window(start, end, excluded, requested_end)


def protected_reason(day, today: date, rows, financial=None) -> str | None:
	"""Why this employee-day must not be rebuilt, or None. Pure.

	`rows` are the day's Attendance rows (any docstatus); `financial` is what
	`_repair_financial_dependency` returned for the day.
	"""
	day = getdate(day)
	if day >= today:
		return "today or later: never touched"
	for row in rows:
		if cint(row.get("docstatus")) == 2:
			continue
		name = row.get("name")
		if cint(row.get("docstatus")) == 0:
			return f"{name} is a draft attendance HR is keying"
		if row.get("leave_type") or row.get("leave_application") or row.get("status") == "On Leave":
			return f"{name} is a leave record"
		if cint(row.get("modify_half_day_status")):
			return f"{name} is a half-day leave"
		if row.get("attendance_request"):
			return f"{name} comes from an Attendance Request"
		if not cint(row.get("auto_attendance")):
			return f"{name} was marked by HR by hand"
	if financial:
		return f"approved overtime or submitted payroll depends on this day ({financial})"
	return None


def _minutes(value) -> int:
	"""Minutes past midnight of a Shift Type time (timedelta, time, datetime or 'HH:MM:SS')."""
	if isinstance(value, timedelta):
		return int(value.total_seconds() // 60) % (24 * 60)
	if isinstance(value, datetime | time):
		return value.hour * 60 + value.minute
	hours, minutes = str(value).split(":")[:2]
	return int(hours) * 60 + int(minutes)


def is_night_shift(start_time, end_time) -> bool:
	"""Starts 18:00 or later and ends before 06:00. Pure."""
	return _minutes(start_time) >= NIGHT_START_MIN and _minutes(end_time) < NIGHT_END_MAX


def in_shift_window(moment, start_time, end_time) -> bool:
	"""Is the clock time inside the SCHEDULED start..end (no check-in buffers)? Pure.

	The 360-minute buffers are left out on purpose: with them a 19:30-03:30
	window spans 13:30-09:30 and swallows every day worker's punch, so nothing
	could ever be proven unused.
	"""
	minute, start, end = _minutes(get_datetime(moment)), _minutes(start_time), _minutes(end_time)
	if start <= end:
		return start <= minute <= end
	return minute >= start or minute <= end


def night_assignment_unused(punch_times, start_time, end_time) -> bool:
	"""True when no punch in the assignment's whole range lies inside its window. Pure."""
	return not any(in_shift_window(moment, start_time, end_time) for moment in punch_times)


def is_mirrored_release_candidate(row) -> bool:
	"""A mirrored, submitted, automation-owned Absent (or 0 h Half Day). Pure.

	Leave, HR hand-marked, Attendance Request and worked rows never qualify.
	"""
	return bool(
		row.get("synced_from_instance")
		and cint(row.get("docstatus")) == 1
		and cint(row.get("auto_attendance"))
		and not row.get("leave_type")
		and not row.get("leave_application")
		and not row.get("attendance_request")
		and not cint(row.get("modify_half_day_status"))
		and (
			row.get("status") == "Absent"
			or (row.get("status") == "Half Day" and not flt(row.get("working_hours")))
		)
	)


def split_by_held_dates(planned, held) -> tuple[list, list]:
	"""(dates safe to run a whole-date repair on, extra held rows). Pure.

	`repair_attendance_days`, `recover_overwritten_checkins` and
	`import_missing_checkins` take a date window and no employee, so a date that
	holds one protected day cannot be run for anyone.
	"""
	# ceiling: whole-date granularity, upgrade: add an employee filter to those three tools
	bad = {str(h["date"]) for h in held}
	dates, more_held = set(), []
	for entry in planned:
		day = str(entry["date"])
		if day in bad:
			more_held.append(
				{
					**entry,
					"date": day,
					"reason": "shares its date with a held-back day; this tool cannot run for one employee",
					"hr": False,
				}
			)
		else:
			dates.add(day)
	logger.debug("[attendance_recovery] %d date(s) clear, %d row(s) held by date", len(dates), len(more_held))
	return sorted(dates), more_held


# --- reads ----------------------------------------------------------------------


def _today() -> date:
	return getdate(now_datetime())


def _require_operator(action: str) -> None:
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced(_(action))


def _window(from_date, to_date) -> Window:
	try:
		return recovery_window(from_date, to_date, _today())
	except ValueError as exc:
		frappe.throw(str(exc))


def _attendance_rows(employee, day) -> list:
	logger.debug("[attendance_recovery] attendance of %s on %s", employee, day)
	return frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": getdate(day), "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
	)


def _financial(employee, day, rows, for_update):
	"""The payout depending on the day, or None. Reads with no lock in a dry run."""
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	submitted = next((r.get("name") for r in rows if cint(r.get("docstatus")) == 1), None)
	found = _repair_financial_dependency(employee, getdate(day), submitted, for_update=for_update)
	if found:
		logger.info("[attendance_recovery] %s on %s depends on %s", employee, day, found)
	return found


def _held(entry, reason, hr=True) -> dict:
	return {
		**entry,
		"employee": entry.get("employee"),
		"date": str(entry.get("date")),
		"reason": reason,
		"hr": hr,
	}


def _day_protection(employee, day, for_update, ignore=None) -> str | None:
	rows = [r for r in _attendance_rows(employee, day) if r.get("name") != ignore]
	return protected_reason(day, _today(), rows, _financial(employee, day, rows, for_update))


def _outcome(planned=None, held=None, **extra) -> dict:
	held = held or []
	return {"planned": planned or [], "held_back": held, "hr_list": [h for h in held if h.get("hr")], **extra}


def _submitted_assignments(start, end) -> list:
	logger.debug("[attendance_recovery] active assignments over %s..%s", start, end)
	return frappe.get_all(
		"Shift Assignment",
		filters={"docstatus": 1, "status": "Active", "start_date": ["<=", end]},
		or_filters=[["end_date", ">=", start], ["end_date", "is", "not set"]],
		fields=["name", "employee", "shift_type", "start_date", "end_date", "synced_from_instance"],
		limit_page_length=0,
	)


def _shift_times(names) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"Shift Type", filters={"name": ["in", sorted(names)]}, fields=["name", "start_time", "end_time"]
	)
	return {r.name: (r.start_time, r.end_time) for r in rows}


def _local_punches(employee, start, end) -> list:
	"""The employee's own (unmirrored, unrejected) punches in [start, end)."""
	rows = frappe.get_all(
		"Employee Checkin",
		filters=[
			["employee", "=", employee],
			["time", ">=", start],
			["time", "<", end],
			["synced_from_instance", "is", "not set"],
		],
		fields=["name", "time", "log_type", "shift", "shift_start", "remote_approval_status"],
		order_by="time asc",
		limit_page_length=0,
	)
	kept = [r for r in rows if r.get("remote_approval_status") != "Rejected"]
	logger.debug("[attendance_recovery] %s: %d punch(es) in %s..%s", employee, len(kept), start, end)
	return kept


# --- 1. assignments ----------------------------------------------------------------


def _overlap(night, day_assignments, win):
	"""(first, last) date the night assignment shares with a day assignment inside the window."""
	spans = []
	for day in day_assignments:
		first = max(getdate(night.start_date), getdate(day.start_date), win.start)
		last = min(
			getdate(night.end_date) if night.end_date else win.end,
			getdate(day.end_date) if day.end_date else win.end,
			win.end,
		)
		if first <= last:
			spans.append((first, last))
	if not spans:
		return None
	return min(s for s, _e in spans), max(e for _s, e in spans)


def _plan_assignments(win, for_update=False) -> dict:
	"""Night assignments overlapping a day assignment; planned only when never used."""
	rows = _submitted_assignments(win.start, win.end)
	times = _shift_times({r.shift_type for r in rows})
	night_types = {name for name, (start, end) in times.items() if is_night_shift(start, end)}
	by_employee = {}
	for row in rows:
		by_employee.setdefault(row.employee, []).append(row)

	planned, held = [], []
	for employee, assignments in sorted(by_employee.items()):
		days = [a for a in assignments if a.shift_type not in night_types]
		for night in (a for a in assignments if a.shift_type in night_types):
			span = _overlap(night, days, win)
			if not span:
				continue
			entry = {
				"employee": employee,
				"date": str(span[0]),
				"to_date": str(span[1]),
				"assignment": night.name,
				"shift_type": night.shift_type,
				"day_assignments": [d.name for d in days],
			}
			range_start = getdate(night.start_date)
			if range_start > win.end:
				held.append(_held(entry, "starts today or later: it cannot be proven unused yet"))
				continue
			# The whole range up to now, today included: a night punch today still proves use.
			punches = _local_punches(
				employee, datetime.combine(range_start, time.min), get_datetime(now_datetime())
			)
			start_time, end_time = times[night.shift_type]
			inside = [p for p in punches if in_shift_window(p.time, start_time, end_time)]
			entry["night_window_punches"] = len(inside)
			entry["daytime_punches"] = sum(
				1
				for p in punches
				if span[0] <= getdate(p.time) <= span[1] and not in_shift_window(p.time, start_time, end_time)
			)
			if inside:
				held.append(
					_held(
						entry,
						f"a punch at {inside[0].time} lies inside the night window: HR decides which shift is real",
					)
				)
				continue
			stamped_days = sorted(
				{getdate(p.shift_start or p.time) for p in punches if p.shift == night.shift_type}
			)
			reason = next(
				(
					f"{day}: {why}"
					for day in stamped_days
					if day <= win.end
					for why in [_day_protection(employee, day, for_update)]
					if why
				),
				None,
			)
			if reason:
				held.append(_held(entry, reason))
				continue
			planned.append(entry)
	logger.info(
		"[attendance_recovery] assignments %s..%s: %d unused night assignment(s), %d for HR",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _shift_evidence(doc) -> bool:
	"""Does any punch or attendance still carry this assignment's shift? on_cancel would refuse."""
	filters = {"employee": doc.employee, "shift": doc.shift_type}
	found = bool(
		frappe.db.exists("Employee Checkin", {**filters, "time": [">=", doc.start_date]})
		or frappe.db.exists(
			"Attendance", {**filters, "attendance_date": [">=", doc.start_date], "docstatus": ["<", 2]}
		)
	)
	logger.debug("[attendance_recovery] %s still stamped on rows: %s", doc.name, found)
	return found


def _end_assignment(entry, win) -> dict:
	doc = frappe.get_doc("Shift Assignment", entry["assignment"])
	doc.flags.ignore_permissions = True
	if _shift_evidence(doc):
		# Shift Assignment.on_cancel refuses while a punch or attendance carries the
		# shift. Inactive drops it from shift resolution (status == "Active" filter)
		# and keeps the history; the end date records when it was ended.
		end = max(getdate(doc.start_date), win.end)
		if doc.end_date and getdate(doc.end_date) < end:
			end = getdate(doc.end_date)
		doc.status = "Inactive"
		doc.end_date = end
		doc.save()
		action = f"set Inactive, end date {end}"
	else:
		doc.cancel()
		action = "cancelled"
	doc.add_comment(
		"Comment",
		_("Attendance recovery by {0}: {1}. No punch of this employee fell inside the shift window.").format(
			frappe.session.user, action
		),
	)
	logger.info("[attendance_recovery] %s %s", entry["assignment"], action)
	return {**entry, "action": action}


def _apply_assignments(win, plan) -> dict:
	done, held = [], []
	for entry in plan["planned"]:
		result, error = _guarded(entry["assignment"], lambda entry=entry: _end_assignment(entry, win))
		if error:
			held.append(_held(entry, f"could not be ended: {error}"))
		else:
			done.append(result)
	return {"done": done, "held_back": held}


# --- 2. overwritten -----------------------------------------------------------------


def _recovery_inserts(start, end) -> list:
	from hrms.sync.checkin_recovery import collect

	plan = collect(str(start), str(end))["plan"]
	inserts = [e for e in plan if e.get("action") == "insert"]
	logger.debug(
		"[attendance_recovery] %d overwritten punch(es) to re-insert %s..%s", len(inserts), start, end
	)
	return inserts


def _plan_overwritten(win, for_update=False) -> dict:
	planned, held = [], []
	for entry in _recovery_inserts(win.start, win.end):
		row = {
			"employee": entry["employee"],
			"date": str(getdate(entry["time"])),
			"time": str(entry["time"]),
			"log_type": entry.get("log_type"),
			"source_name": entry.get("source_name"),
			"confidence": entry.get("confidence"),
		}
		reason = _day_protection(row["employee"], row["date"], for_update)
		(held.append(_held(row, reason)) if reason else planned.append(row))
	logger.info("[attendance_recovery] overwritten: %d planned, %d held", len(planned), len(held))
	return _outcome(planned, held)


def _apply_dated(plan, preview, run, label) -> dict:
	"""Run a date-window tool one clear date at a time, re-checking that date first."""
	dates, more_held = split_by_held_dates(plan["planned"], plan["held_back"])
	allowed = {(e["employee"], str(e["date"])) for e in plan["planned"] + plan.get("noop", [])}
	done, held = [], list(more_held)
	for day in dates:
		keys = preview(day)
		strangers = [k for k in keys if k not in allowed]
		if strangers:
			held.extend(
				_held(
					{"employee": e, "date": d},
					f"{label} on {day} now also touches this day; re-run the dry run",
					hr=False,
				)
				for e, d in strangers
			)
			continue
		result, error = _guarded(f"{label} {day}", lambda day=day: run(day))
		if error:
			held.extend(
				_held(e, f"{label} failed: {error}", hr=False)
				for e in plan["planned"]
				if str(e["date"]) == day
			)
		else:
			done.append({"date": day, "result": result})
	logger.info("[attendance_recovery] %s: %d date(s) applied, %d row(s) held", label, len(done), len(held))
	return {"done": done, "held_back": held}


def _apply_overwritten(win, plan) -> dict:
	from hrms.sync.checkin_recovery import recover_overwritten_checkins

	def preview(day):
		return [(e["employee"], str(getdate(e["time"]))) for e in _recovery_inserts(day, day)]

	def run(day):
		result = recover_overwritten_checkins(day, day, dry_run=0)
		return {"inserted": result.get("inserted"), "failed": result.get("failed")}

	return _apply_dated(plan, preview, run, "overwritten punch recovery")


# --- 3. mirrored rows -----------------------------------------------------------------


def _hub_punch_days(employees, start, end) -> set:
	if not employees:
		return set()
	rows = frappe.get_all(
		"Employee Checkin",
		filters=[
			["employee", "in", sorted(employees)],
			["time", ">=", datetime.combine(start, time.min)],
			["time", "<", datetime.combine(end + timedelta(days=2), time.min)],
			["synced_from_instance", "is", "not set"],
		],
		fields=["employee", "time", "shift_start", "remote_approval_status"],
		limit_page_length=0,
	)
	days = {
		(r.employee, getdate(r.shift_start or r.time))
		for r in rows
		if r.get("remote_approval_status") != "Rejected"
	}
	logger.debug(
		"[attendance_recovery] %d hub-punched day(s) among %d employee(s)", len(days), len(employees)
	)
	return days


def _plan_mirrored_rows(win, for_update=False) -> dict:
	end = min(win.end, CUTOVER - timedelta(days=1))
	if win.start > end:
		return _outcome(note=f"no day before the cutover ({CUTOVER}) in this window")
	rows = frappe.get_all(
		"Attendance",
		filters={
			"docstatus": 1,
			"synced_from_instance": ["is", "set"],
			"attendance_date": ["between", [win.start, end]],
		},
		fields=ATTENDANCE_FIELDS,
		limit_page_length=0,
	)
	candidates = [r for r in rows if is_mirrored_release_candidate(r)]
	punched = _hub_punch_days({r.employee for r in candidates}, win.start, end)
	planned, held = [], []
	for row in candidates:
		day = getdate(row.attendance_date)
		if (row.employee, day) not in punched:
			continue
		entry = {"employee": row.employee, "date": str(day), "attendance": row.name, "status": row.status}
		reason = _day_protection(row.employee, day, for_update, ignore=row.name)
		(held.append(_held(entry, reason)) if reason else planned.append(entry))
	logger.info(
		"[attendance_recovery] mirrored rows %s..%s: %d mirrored, %d releasable, %d held",
		win.start,
		end,
		len(rows),
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _release_mirrored(entry) -> dict:
	doc = frappe.get_doc("Attendance", entry["attendance"])
	doc.flags.ignore_permissions = True
	# Through the document: write_block's before_cancel decides (cutover unlock,
	# or a logged System Manager break-glass); on_cancel unlinks the punches.
	doc.cancel()
	doc.add_comment(
		"Comment",
		_(
			"Attendance recovery by {0}: mirrored {1} cancelled so this hub marks the day from its own punches."
		).format(frappe.session.user, entry.get("status")),
	)
	logger.info("[attendance_recovery] released mirrored %s (%s)", entry["attendance"], entry["date"])
	return entry


def _apply_mirrored_rows(win, plan) -> dict:
	done, held = [], []
	for entry in plan["planned"]:
		result, error = _guarded(entry["attendance"], lambda entry=entry: _release_mirrored(entry))
		if error:
			held.append(_held(entry, f"could not be cancelled: {error}"))
		else:
			done.append(result)
	return {"done": done, "held_back": held}


# --- 4. import ---------------------------------------------------------------------------


def _source_instance() -> str | None:
	"""The one enabled ERP instance that carries credentials, or None."""
	rows = frappe.get_all(
		"HRMS ERP Instance", filters={"enabled": 1}, fields=["name", "url", "api_key"], limit_page_length=0
	)
	usable = [r.name for r in rows if r.get("url") and r.get("api_key")]
	logger.debug("[attendance_recovery] usable ERP instances: %s", usable)
	return usable[0] if len(usable) == 1 else None


def _import_preview(instance, start, end) -> dict:
	from hrms.sync.checkin_import import import_missing_checkins

	return import_missing_checkins(instance=instance, from_date=str(start), to_date=str(end), dry_run=1)


def _plan_import(win, for_update=False) -> dict:
	instance = _source_instance()
	if not instance:
		return _outcome(note="no single enabled ERP instance with credentials: nothing to import")
	result = _import_preview(instance, win.start, win.end)
	planned, held = [], []
	for sample in result.get("inserts") or []:
		entry = {**sample, "date": sample["attendance_day"]}
		reason = _day_protection(entry["employee"], entry["date"], for_update)
		(held.append(_held(entry, reason)) if reason else planned.append(entry))
	count = max(int(result.get("to_insert") or 0) - len(held), len(planned))
	logger.info("[attendance_recovery] import from %s: %d to insert, %d held", instance, count, len(held))
	return _outcome(planned, held, planned_count=count, instance=instance)


def _apply_import(win, plan) -> dict:
	from hrms.sync.checkin_import import import_missing_checkins

	instance = plan.get("instance")
	done, held = [], []
	day = win.start
	while instance and day <= win.end:
		preview = _import_preview(instance, day, day)
		samples = preview.get("inserts") or []
		if int(preview.get("to_insert") or 0) > len(samples):
			held.append(
				_held(
					{"employee": None, "date": day},
					"too many punches to check one by one; import this date by hand",
					hr=False,
				)
			)
		elif samples:
			reasons = [(s, _day_protection(s["employee"], s["attendance_day"], True)) for s in samples]
			blocked = [(s, r) for s, r in reasons if r]
			if blocked:
				held.extend(_held({**s, "date": s["attendance_day"]}, r) for s, r in blocked)
			else:
				result, error = _guarded(
					f"import {day}",
					lambda day=day: import_missing_checkins(
						instance=instance, from_date=str(day), to_date=str(day), dry_run=0
					),
				)
				if error:
					held.append(_held({"employee": None, "date": day}, f"import failed: {error}", hr=False))
				else:
					done.append(
						{
							"date": str(day),
							"inserted": result.get("inserted"),
							"errored": result.get("errored"),
						}
					)
		day += timedelta(days=1)
	logger.info("[attendance_recovery] import applied on %d date(s), %d held", len(done), len(held))
	return {"done": done, "held_back": held}


# --- 5. heal ---------------------------------------------------------------------------------


def _plan_heal(win, for_update=False) -> dict:
	from hrms.utils import offshift_punch_heal

	result = offshift_punch_heal.heal_offshift_punches(
		from_date=str(win.start), to_date=str(win.end), dry_run=1, not_before=str(REPAIR_FLOOR)
	)
	planned, held = [], []
	for entry in result.get("healed") or []:
		row = {k: entry.get(k) for k in ("checkin", "employee", "time", "log_type", "shift")}
		row["date"] = entry["shift_date"]
		reason = _day_protection(row["employee"], row["date"], for_update)
		(held.append(_held(row, reason)) if reason else planned.append(row))
	for entry in result.get("held_back") or []:
		held.append(
			_held(
				{
					"checkin": entry.get("checkin"),
					"employee": entry.get("employee"),
					"date": entry.get("shift_date"),
				},
				entry.get("held_because") or "held back by the heal",
			)
		)
	for entry in result.get("not_readable") or []:
		held.append(
			_held(
				{
					"checkin": entry.get("checkin"),
					"employee": entry.get("employee"),
					"date": entry.get("shift_date"),
				},
				entry.get("held_because")
				or f"shift {entry.get('shift')} is one the attendance job never reads",
			)
		)
	logger.info("[attendance_recovery] heal: %d planned, %d held", len(planned), len(held))
	return _outcome(planned, held)


def _apply_heal(win, plan) -> dict:
	"""Heal per (employee, clock date) through `_heal`, the heal's own per-row writer.

	`heal_offshift_punches` would also enqueue a whole-shift-type
	process_auto_attendance, which marks today too; the rebuild step re-marks
	only days up to yesterday instead.
	"""
	from hrms.utils import offshift_punch_heal

	blocked = {(h.get("employee"), getdate(h["time"])) for h in plan["held_back"] if h.get("time")}
	groups = sorted({(e["employee"], getdate(e["time"])) for e in plan["planned"]})
	done, held = [], []
	for employee, clock_day in groups:
		entries = [e for e in plan["planned"] if (e["employee"], getdate(e["time"])) == (employee, clock_day)]
		if (employee, clock_day) in blocked:
			held.extend(
				_held(e, "another punch that day is held back; healed with it by hand", hr=False)
				for e in entries
			)
			continue
		start = datetime.combine(clock_day, time.min)
		result, error = _guarded(
			f"heal {employee} {clock_day}",
			lambda employee=employee, start=start: offshift_punch_heal._heal(
				start,
				start + timedelta(days=1),
				dry_run=False,
				for_update=True,
				employee=employee,
				not_before=REPAIR_FLOOR,
			),
		)
		if error:
			held.extend(_held(e, f"heal failed: {error}", hr=False) for e in entries)
			continue
		done.extend(
			{"checkin": h["checkin"], "employee": employee, "date": h["shift_date"], "shift": h["shift"]}
			for h in result["healed"]
		)
		held.extend(
			_held({**h, "date": h.get("shift_date")}, h.get("held_because") or "held back by the heal")
			for h in result["held_back"] + result["not_readable"]
		)
	logger.info("[attendance_recovery] heal applied: %d punch(es), %d held", len(done), len(held))
	return {"done": done, "held_back": held}


# --- 6. skip stamps ---------------------------------------------------------------------------


def _refetch_changes(punch_names) -> bool:
	"""Would fetch_shift give any of these punches another shift? Nothing is saved."""
	# ceiling: each punch is re-resolved alone against the stored rows, as the audit's
	# apply loop does; upgrade: carry resolved shifts forward if a day re-plans forever
	for name in punch_names:
		punch = frappe.get_doc("Employee Checkin", name)
		was = punch.shift
		punch.attendance = None
		punch.fetch_shift()
		if punch.shift != was:
			logger.debug("[attendance_recovery] %s would move %s -> %s", name, was, punch.shift)
			return True
	return False


def _audit_plan(start, end, for_update=False) -> tuple[list, list, set]:
	from hrms.utils import attendance_day_audit as audit

	days = audit.collect(str(start), str(end))["days"]
	locked = audit._financially_locked(days, for_update=for_update)
	logger.debug(
		"[attendance_recovery] audit %s..%s: %d day(s), %d locked", start, end, len(days), len(locked)
	)
	return days, audit.plan_repairs(days, locked), locked


def _plan_skip_stamps(win, for_update=False) -> dict:
	days, repairs, locked = _audit_plan(win.start, win.end)
	planned, held, noop = [], [], []
	for entry in repairs:
		row = {
			"employee": entry["employee"],
			"date": str(entry["date"]),
			"action": entry["action"],
			"punches": entry["punches"],
		}
		if entry["action"] == "refetch-shift" and not _refetch_changes(entry["punches"]):
			noop.append(row)
			continue
		reason = _day_protection(row["employee"], row["date"], for_update)
		(held.append(_held(row, reason)) if reason else planned.append(row))
	held.extend(
		_held(
			{"employee": e, "date": d, "action": "refetch-shift"},
			"approved overtime or submitted payroll depends on this day",
		)
		for e, d in sorted(locked)
	)
	causes = Counter(d["detail"].split(": ", 1)[-1] for d in days if d["verdict"] == "punches-skip-stamped")
	verdicts = Counter(d["verdict"] for d in days)
	logger.info(
		"[attendance_recovery] skip stamps: %d planned, %d held, %d already right",
		len(planned),
		len(held),
		len(noop),
	)
	return _outcome(planned, held, noop=noop, skip_causes=dict(causes), verdicts=dict(verdicts))


def _apply_skip_stamps(win, plan) -> dict:
	from hrms.utils.attendance_day_audit import repair_attendance_days

	def preview(day):
		return [(e["employee"], str(e["date"])) for e in _audit_plan(day, day)[1]]

	def run(day):
		result = repair_attendance_days(day, day, dry_run=0)
		return {"touched": result.get("touched"), "unchanged": result.get("unchanged")}

	return _apply_dated(plan, preview, run, "attendance day audit repair")


# --- 7. rebuild ------------------------------------------------------------------------------------


def _remark_day(employee, day, apply):
	from hrms.sync.checkin_import import _remark_day as engine_remark

	return engine_remark(employee, getdate(day), apply)


def _plan_rebuild(win, for_update=False) -> dict:
	"""Days holding punches the engine would read (shift set, unlinked, not skipped)."""
	rows = frappe.get_all(
		"Employee Checkin",
		filters=[
			["shift", "is", "set"],
			["attendance", "is", "not set"],
			["skip_auto_attendance", "=", 0],
			["synced_from_instance", "is", "not set"],
			["shift_start", ">=", datetime.combine(win.start, time.min)],
			["shift_start", "<", datetime.combine(win.end + timedelta(days=1), time.min)],
		],
		fields=["employee", "shift_start"],
		limit_page_length=0,
	)
	days = sorted({(r.employee, getdate(r.shift_start)) for r in rows})
	planned, held = [], []
	for employee, day in days:
		if not (win.start <= day <= win.end):
			continue
		entry = {"employee": employee, "date": str(day)}
		reason = _day_protection(employee, day, for_update)
		if reason:
			held.append(_held(entry, reason))
			continue
		preview = _remark_day(employee, day, False) or {}
		action = preview.get("action")
		if action == "remark":
			expected = preview.get("expected") or []
			if expected and not any(e.get("status") for e in expected):
				held.append(
					_held(
						entry,
						"the engine would not mark this day: "
						+ "; ".join(e.get("detail") or "" for e in expected),
					)
				)
				continue
			planned.append({**entry, "expected": expected, "attendance": preview.get("attendance")})
		elif action in ("hr-owned", "locked"):
			held.append(_held(entry, preview.get("detail") or action))
	logger.info(
		"[attendance_recovery] rebuild %s..%s: %d day(s) planned, %d held",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


# --- 7b. leftover rows ---------------------------------------------------------------------------------


def punch_in_row_window(moment, day, start_time, end_time) -> bool:
	"""Is the punch inside the row's SCHEDULED shift (no buffers) on that shift day? Pure."""
	moment, day = get_datetime(moment), getdate(day)
	minute, start, end = _minutes(moment), _minutes(start_time), _minutes(end_time)
	logger.debug("[attendance_recovery] punch %s against %s..%s on %s", moment, start_time, end_time, day)
	if start <= end:
		return moment.date() == day and start <= minute <= end
	return (moment.date() == day and minute >= start) or (
		moment.date() == day + timedelta(days=1) and minute <= end
	)


def _real_row(row, others):
	"""The worked row of the same day: submitted, another shift, Present/Half Day, punches linked."""
	real = next(
		(
			o
			for o in others
			if cint(o.get("docstatus")) == 1
			and o.get("shift") != row.get("shift")
			and o.get("status") in ("Present", "Half Day")
			and o.get("linked")
		),
		None,
	)
	logger.debug("[attendance_recovery] real row beside %s: %s", row.get("name"), real and real.get("name"))
	return real


def leftover_verdict(
	row, others, *, linked, punch_times, window, night, assignment_ended, today, financial=None
) -> str | None:
	"""None when this row is an empty leftover of a rebuilt split day and may be cancelled;
	otherwise the first condition it fails. Pure.

	`others`: the employee's other rows that date, each with `linked` (has punches).
	`window`: the row's shift (start, end) or None.
	"""
	name, shift, day = row.get("name"), row.get("shift"), getdate(row.get("attendance_date"))
	logger.debug("[attendance_recovery] judging leftover %s (%s on %s)", name, shift, day)
	if cint(row.get("docstatus")) != 1:
		return f"{name} is not a submitted row"
	if day >= today:
		return "today or later: never touched"
	if not cint(row.get("auto_attendance")):
		return f"{name} was marked by HR by hand"
	if row.get("leave_type") or row.get("leave_application") or row.get("status") == "On Leave":
		return f"{name} is a leave record"
	if cint(row.get("modify_half_day_status")):
		return f"{name} is a half-day leave"
	if row.get("attendance_request"):
		return f"{name} comes from an Attendance Request"
	if linked:
		return f"a punch is still linked to {name}"
	if window:
		inside = next((m for m in punch_times if punch_in_row_window(m, day, *window)), None)
		if inside:
			return f"a punch at {inside} lies inside the {shift} window on {day}"
	if not _real_row(row, others):
		return "no other submitted Present / Half Day row with punches under another shift marks the real day"
	if not night and not assignment_ended:
		return f"{shift} is not a night shift and its assignment was not ended by attendance recovery"
	if financial:
		return f"approved overtime or submitted payroll depends on this day ({financial})"
	return None


def _assignment_ended_by_recovery(employee, shift, day) -> bool:
	"""Was the assignment covering `day` for this shift ended or cancelled by the assignments step?"""
	rows = frappe.get_all(
		"Shift Assignment",
		filters=[
			["employee", "=", employee],
			["shift_type", "=", shift],
			["start_date", "<=", day],
			["docstatus", "in", [1, 2]],
		],
		or_filters=[["end_date", ">=", day], ["end_date", "is", "not set"]],
		fields=["name", "status", "docstatus"],
	)
	ended = [r.name for r in rows if cint(r.docstatus) == 2 or r.status == "Inactive"]
	found = bool(ended) and bool(
		frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Shift Assignment",
				"reference_name": ["in", ended],
				"content": ["like", "%Attendance recovery by%"],
			},
			limit_page_length=1,
		)
	)
	logger.debug("[attendance_recovery] %s %s on %s ended by recovery: %s", employee, shift, day, found)
	return found


def _plan_leftover_rows(win, for_update=False) -> dict:
	"""Empty rows a rebuilt split day left under another shift. Only days with 2+ rows are read."""
	rows = frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "attendance_date": ["between", [win.start, win.end]]},
		fields=[*ATTENDANCE_FIELDS, "shift"],
		limit_page_length=0,
	)
	groups = {}
	for row in rows:
		groups.setdefault((row.employee, getdate(row.attendance_date)), []).append(row)
	times = _shift_times({r.shift for r in rows if r.shift})
	planned, held = [], []
	for (employee, day), group in sorted(groups.items()):
		if len(group) < 2:
			continue
		linked = {r.name: bool(frappe.db.exists("Employee Checkin", {"attendance": r.name})) for r in group}
		punch_times = None
		for row in group:
			if linked[row.name]:
				continue  # a worked row, never a leftover
			if punch_times is None:
				start = datetime.combine(day, time.min)
				punch_times = [p.time for p in _local_punches(employee, start, start + timedelta(days=2))]
			others = [{**o, "linked": linked[o.name]} for o in group if o.name != row.name]
			window = times.get(row.shift)
			args = {
				"linked": False,
				"punch_times": punch_times,
				"window": window,
				"night": bool(window and is_night_shift(*window)),
				"assignment_ended": bool(
					row.shift and _assignment_ended_by_recovery(employee, row.shift, day)
				),
				"today": _today(),
			}
			reason = leftover_verdict(row, others, **args)
			if reason is None:
				reason = leftover_verdict(
					row, others, **args, financial=_financial(employee, day, [row], for_update)
				)
			real = _real_row(row, others) or {}
			entry = {
				"employee": employee,
				"date": str(day),
				"attendance": row.name,
				"shift": row.shift,
				"status": row.status,
				"real_row": real.get("name"),
				"real_shift": real.get("shift"),
			}
			(held.append(_held(entry, reason)) if reason else planned.append(entry))
	logger.info(
		"[attendance_recovery] leftover rows %s..%s: %d to cancel, %d for HR",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _cancel_leftover(entry) -> dict:
	doc = frappe.get_doc("Attendance", entry["attendance"])
	doc.flags.ignore_permissions = True
	# Through the document, as for mirrored rows: write_block's before_cancel judges
	# a mirrored row; on_cancel unlinks nothing because nothing is linked.
	doc.cancel()
	doc.add_comment(
		"Comment",
		_("Cancelled by attendance recovery: empty {0} row left after the day was rebuilt under {1}").format(
			entry["shift"], entry["real_shift"]
		),
	)
	logger.info(
		"[attendance_recovery] cancelled leftover %s (%s, real %s)",
		entry["attendance"],
		entry["shift"],
		entry["real_row"],
	)
	return entry


def _apply_leftover_rows(win, plan) -> dict:
	done, held = [], []
	for entry in plan["planned"]:
		result, error = _guarded(entry["attendance"], lambda entry=entry: _cancel_leftover(entry))
		if error:
			held.append(_held(entry, f"could not be cancelled: {error}"))
		else:
			done.append(result)
	logger.info("[attendance_recovery] leftover rows: %d cancelled, %d held", len(done), len(held))
	return {"done": done, "held_back": held}


def _rebuild_day(entry, win) -> dict:
	day = getdate(entry["date"])
	if day > win.end:
		raise frappe.ValidationError(f"{day} is today or later")
	result = _remark_day(entry["employee"], day, True) or {}
	for name in result.get("marked") or []:
		frappe.get_doc("Attendance", name).add_comment(
			"Comment",
			_("Attendance recovery by {0}: rebuilt from this day's punches.").format(frappe.session.user),
		)
	logger.info("[attendance_recovery] rebuilt %s on %s: %s", entry["employee"], day, result.get("marked"))
	return result


def _apply_rebuild(win, plan) -> dict:
	done, held = [], []
	for entry in plan["planned"]:
		result, error = _guarded(
			f"rebuild {entry['employee']} {entry['date']}", lambda entry=entry: _rebuild_day(entry, win)
		)
		if error:
			held.append(_held(entry, f"rebuild failed: {error}", hr=False))
		elif result.get("marked"):
			done.append({"employee": entry["employee"], "date": entry["date"], "marked": result["marked"]})
		else:
			held.append(
				_held(entry, "; ".join(result.get("errors") or []) or result.get("detail") or "not marked")
			)
	return {"done": done, "held_back": held}


# --- 8. OT recount ------------------------------------------------------------------------------------


def _plan_ot_recount(win, for_update=False) -> dict:
	"""What recompute_ot_backfill would change. It also recounts HR hand-marked rows
	that have punches — exactly as it does on every deploy (after_migrate)."""
	from hrms.hr.doctype.attendance.attendance import recompute_ot_backfill

	result = recompute_ot_backfill(str(win.start), str(win.end), dry_run=1)
	records = result.get("records") if isinstance(result.get("records"), list) else []
	planned, held = [], []
	for rec in records:
		entry = {**rec, "date": str(rec["date"])}
		paid = _financial(
			rec["employee"], rec["date"], [{"name": rec["attendance"], "docstatus": 1}], for_update
		)
		(
			held.append(_held(entry, f"a payout depends on this day ({paid})"))
			if paid
			else planned.append(entry)
		)
	logger.info("[attendance_recovery] OT recount: %d change(s), %d held", len(planned), len(held))
	return _outcome(planned, held)


def _apply_ot_recount(win, plan) -> dict:
	from hrms.hr.doctype.attendance.attendance import recompute_ot_backfill

	result = recompute_ot_backfill(str(win.start), str(win.end), dry_run=0)
	skipped = result.get("skipped") if isinstance(result.get("skipped"), list) else []
	records = result.get("records") if isinstance(result.get("records"), list) else []
	skipped_names = {s["attendance"] for s in skipped}
	logger.info("[attendance_recovery] OT recount wrote %s", result.get("written"))
	return {
		"done": [r for r in records if r["attendance"] not in skipped_names],
		"held_back": [_held({**s, "date": str(s["date"])}, "a payout depends on this day") for s in skipped],
	}


# --- the envelope -------------------------------------------------------------------------------------


def _guarded(label, fn):
	"""(result, None) or (None, error text). One bad row never stops the rest —
	except a lost transaction, re-raised because the earlier writes are gone."""
	frappe.db.savepoint(ROW_SAVEPOINT)
	try:
		return fn(), None
	except Exception as exc:
		if _lost_transaction(exc):
			raise
		frappe.db.rollback(save_point=ROW_SAVEPOINT)
		logger.exception("[attendance_recovery] %s failed; moving on", label)
		try:
			frappe.log_error(title="Attendance recovery skipped a row", message=f"{label}: {exc}")
		except Exception:
			logger.exception("[attendance_recovery] could not record the failure of %s", label)
		return None, str(exc)


_PLANNERS = {
	"assignments": _plan_assignments,
	"overwritten": _plan_overwritten,
	"mirrored_rows": _plan_mirrored_rows,
	"import": _plan_import,
	"heal": _plan_heal,
	"skip_stamps": _plan_skip_stamps,
	"rebuild": _plan_rebuild,
	"leftover_rows": _plan_leftover_rows,
	"ot_recount": _plan_ot_recount,
}
_APPLIERS = {
	"assignments": _apply_assignments,
	"overwritten": _apply_overwritten,
	"mirrored_rows": _apply_mirrored_rows,
	"import": _apply_import,
	"heal": _apply_heal,
	"skip_stamps": _apply_skip_stamps,
	"rebuild": _apply_rebuild,
	"leftover_rows": _apply_leftover_rows,
	"ot_recount": _apply_ot_recount,
}


def _planned_count(plan) -> int:
	return int(plan.get("planned_count", len(plan.get("planned") or [])))


def _blocked_by(step, win) -> list:
	"""Earlier steps that still have planned work (or could not be planned)."""
	blocked = []
	for earlier in STEPS[: STEPS.index(step)]:
		try:
			count = _planned_count(_PLANNERS[earlier](win, for_update=False))
		except Exception as exc:
			if _lost_transaction(exc):
				raise
			logger.warning("[attendance_recovery] could not plan %s: %s", earlier, exc)
			blocked.append({"step": earlier, "planned": None, "error": str(exc)})
			continue
		if count:
			blocked.append({"step": earlier, "planned": count})
	logger.debug("[attendance_recovery] %s blocked by %s", step, blocked)
	return blocked


@frappe.whitelist(methods=["POST"])
def apply_recovery(step, from_date=None, to_date=None, dry_run=1, force=0) -> dict:
	"""Plan — and with dry_run=0, apply — ONE recovery step. Dry run by default."""
	_require_operator("repair attendance across every company")
	if step not in STEPS:
		frappe.throw(_("Unknown step {0}; the steps are {1}.").format(step, ", ".join(STEPS)))
	dry_run = wants_dry_run(dry_run)
	win = _window(from_date, to_date)
	is_system_manager = "System Manager" in frappe.get_roles()
	blocked = _blocked_by(step, win)
	if not dry_run:
		if blocked and not cint(force):
			frappe.throw(
				_("Run the earlier steps first: {0}.").format(
					", ".join(
						f"{b['step']} ({b['planned'] if b['planned'] is not None else b['error']})"
						for b in blocked
					)
				)
			)
		if blocked and not is_system_manager:
			frappe.throw(_("Only a System Manager may force a step out of order."), frappe.PermissionError)
		if step in SYSTEM_MANAGER_STEPS and not is_system_manager:
			frappe.throw(
				_("Step {0} writes through a System Manager tool.").format(step), frappe.PermissionError
			)
		if blocked:
			logger.warning(
				"[attendance_recovery] %s forced by %s past %s", step, frappe.session.user, blocked
			)

	plan = _PLANNERS[step](win, for_update=not dry_run)
	result = {
		"step": step,
		"dry_run": bool(dry_run),
		"from_date": str(win.start),
		"to_date": str(win.end),
		"excluded_from": str(win.excluded_from) if win.excluded_from else None,
		"blocked_by": blocked,
		"planned": plan.get("planned") or [],
		"planned_count": _planned_count(plan),
		"done": [],
		"held_back": plan.get("held_back") or [],
		"hr_list": plan.get("hr_list") or [],
		**{k: v for k, v in plan.items() if k not in ("planned", "held_back", "hr_list", "planned_count")},
	}
	if not dry_run:
		outcome = _APPLIERS[step](win, plan)
		result["done"] = outcome.get("done") or []
		result["held_back"] = result["held_back"] + (outcome.get("held_back") or [])
		result["hr_list"] = [h for h in result["held_back"] if h.get("hr")]
	logger.info(
		"[attendance_recovery] %s by %s dry_run=%s %s..%s: planned=%d done=%d held=%d hr=%d",
		step,
		frappe.session.user,
		dry_run,
		win.start,
		win.end,
		result["planned_count"],
		len(result["done"]),
		len(result["held_back"]),
		len(result["hr_list"]),
	)
	return result


# --- read-only reports -----------------------------------------------------------------------------------


#: hr_list wording for a request whose hours moved to the shift day before it.
OT_AFTER_SHIFT_DAY = "OT request dated after the shift day — HR to re-date or amend"


def _ot_requests(win) -> list:
	"""Submitted, not rejected OT Requests (pay or replacement leave) dated in the window. One query."""
	rows = frappe.get_all(
		"OT Request",
		filters={
			"docstatus": 1,
			"status": ["!=", "Rejected"],
			"compensation": ["in", ["Overtime Pay", "Replacement Leave"]],
			"ot_date": ["between", [win.start, win.end]],
		},
		fields=["name", "employee", "ot_date", "claimed_hours", "compensation"],
		limit_page_length=0,
	)
	logger.info("[attendance_recovery] %d OT request(s) to price %s..%s", len(rows), win.start, win.end)
	return rows


def _on_submitted_slip(employee, day) -> bool:
	paid = bool(
		frappe.db.exists(
			"Salary Slip",
			{"employee": employee, "start_date": ["<=", day], "end_date": [">=", day], "docstatus": 1},
		)
	)
	logger.debug("[attendance_recovery] %s on %s on a submitted salary slip: %s", employee, day, paid)
	return paid


def _ot_request_review(win) -> dict:
	"""Approved, unpaid OT Requests the shift-day attribution (4b2957884) now prices
	below their claimed hours. Read-only: a pre-deploy check, never a fix."""
	from hrms.utils.ot_calculation import get_day_ot_breakdown

	# ceiling: one calculator run per (employee, request date) and per day before it,
	# memoised; upgrade: price each employee's month once with get_ot_breakdown if
	# this section ever runs long on production.
	memo = {}

	def priced(employee, day):
		if (employee, day) not in memo:
			memo[(employee, day)] = flt(get_day_ot_breakdown(employee, day)["ot_hours"])
		return memo[(employee, day)]

	requests = _ot_requests(win)
	flagged = {"Overtime Pay": [], "Replacement Leave": []}
	for request in requests:
		day = getdate(request.ot_date)
		if _on_submitted_slip(request.employee, day):
			continue
		claimed, now = flt(request.claimed_hours), priced(request.employee, day)
		if now >= claimed:
			continue
		before = day - timedelta(days=1)
		carried = priced(request.employee, before)
		entry = {
			"employee": request.employee,
			"date": str(day),
			"request": request.name,
			"compensation": request.compensation,
			"claimed": claimed,
			"priced_now": now,
			"likely_shift_day": str(before) if carried > 0 else None,
			"shift_day_hours": carried,
		}
		reason = (
			OT_AFTER_SHIFT_DAY
			if carried > 0
			else f"OT request priced at {now} h, under its approved {claimed} h — HR to check"
		)
		flagged[request.compensation].append(_held(entry, reason))
	logger.info(
		"[attendance_recovery] OT requests: %d checked, %d pay and %d leave priced below their claim",
		len(requests),
		len(flagged["Overtime Pay"]),
		len(flagged["Replacement Leave"]),
	)
	return _outcome(
		[],
		flagged["Overtime Pay"] + flagged["Replacement Leave"],
		overtime_pay=flagged["Overtime Pay"],
		replacement_leave=flagged["Replacement Leave"],
		checked=len(requests),
	)


def _section(fix, plan) -> dict:
	planned = plan.get("planned") or []
	return {
		"fix": fix,
		"count": _planned_count(plan),
		"days": len({(p.get("employee"), str(p.get("date"))) for p in planned}),
		"held_back": len(plan.get("held_back") or []),
		"hr_list": len(plan.get("hr_list") or []),
		"sample": planned[:SAMPLE],
		"hr_sample": (plan.get("hr_list") or [])[:SAMPLE],
		**{k: v for k, v in plan.items() if k in ("note", "skip_causes", "verdicts", "instance")},
	}


def _late_checkouts(win) -> dict:
	"""Approved late check-outs whose day still reads Half Day or has no out time."""
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import get_previous_session_checkin

	requests = frappe.get_all(
		"Remote Checkin Request",
		filters={
			"status": "Approved",
			"is_late_checkout": 1,
			"checkin_time": [
				"between",
				[
					datetime.combine(win.start, time.min),
					datetime.combine(win.end + timedelta(days=2), time.min),
				],
			],
		},
		fields=["name", "employee", "checkin", "checkin_time"],
		limit_page_length=0,
	)
	planned, held = [], []
	for request in requests:
		entry = {"employee": request.employee, "request": request.name, "checkin": request.checkin}
		punch = frappe.db.get_value(
			"Employee Checkin", request.checkin, ["time", "shift_start"], as_dict=True
		)
		if not punch:
			held.append(
				_held(
					{**entry, "date": getdate(request.checkin_time)},
					"the approved check-out punch was deleted",
				)
			)
			continue
		anchor = punch.shift_start
		if not anchor:
			previous = get_previous_session_checkin(request.employee, punch.time)
			anchor = previous and frappe.db.get_value("Employee Checkin", previous.name, "shift_start")
		day = getdate(anchor or punch.time)
		if not (win.start <= day <= win.end):
			continue
		rows = _attendance_rows(request.employee, day)
		row = next((r for r in rows if cint(r.get("docstatus")) == 1), None)
		if row and row.status != "Half Day" and row.out_time:
			continue
		entry.update(date=str(day), attendance=row.name if row else None, status=row.status if row else None)
		reason = protected_reason(day, _today(), rows, _financial(request.employee, day, rows, False))
		(held.append(_held(entry, reason)) if reason else planned.append(entry))
	logger.info(
		"[attendance_recovery] late check-outs still broken: %d fixable, %d for HR", len(planned), len(held)
	)
	return _outcome(planned, held)


@frappe.whitelist()
def inputs_report(from_date=str(REPAIR_FLOOR), to_date=None, include_source=0) -> dict:
	"""Every wrong engine input in the window, the step that fixes it, and the days it touches.

	Read-only. The source ERP is read only with include_source=1 — slow and remote,
	so off for the web; from a bench:
	bench --site <site> execute hrms.utils.attendance_recovery.inputs_report --kwargs "{'include_source': 1}"
	"""
	_require_operator("read attendance inputs across every company")
	win = _window(from_date, to_date)
	sections = {}

	def run(key, fn):
		try:
			sections[key] = fn()
		except Exception as exc:
			if _lost_transaction(exc):
				raise
			logger.exception("[attendance_recovery] section %s failed", key)
			sections[key] = {"error": str(exc)}

	def night():
		from hrms.utils.checkin_damage_enumeration import run_shape

		out = _section("assignments", _plan_assignments(win))
		out["s6_duplicate_assignments"] = len(run_shape("S6", str(win.start), str(win.end)))
		out["info_s1_open_sessions"] = len(run_shape("S1", str(win.start), str(win.end)))
		out["info_s2_repair_candidates"] = len(run_shape("S2", str(win.start), str(win.end)))
		return out

	def missing():
		if not cint(include_source):
			return {"fix": "import", "note": "not read: pass include_source=1 (bench execute)"}
		instance = _source_instance()
		if not instance:
			return {"fix": "import", "note": "no single enabled ERP instance with credentials"}
		from hrms.sync.missing_checkins import report

		found = report(instance=instance, from_date=str(win.start), to_date=str(win.end), sample=SAMPLE)
		return {
			**_section("import", _plan_import(win)),
			"missing": found.get("missing"),
			"type_mismatch": found.get("type_mismatch"),
		}

	def excluded():
		if not win.excluded_from:
			return {"fix": None, "count": 0}
		count = frappe.db.count(
			"Employee Checkin",
			{
				"time": [
					"between",
					[
						datetime.combine(win.excluded_from, time.min),
						datetime.combine(win.requested_end, time.max),
					],
				]
			},
		)
		return {
			"fix": None,
			"from_date": str(win.excluded_from),
			"to_date": str(win.requested_end),
			"punches": count,
			"note": "today and later are never touched",
		}

	run("a_wrong_night_assignment", night)
	run("b_shiftless_punches", lambda: _section("heal", _plan_heal(win)))
	run("c_skip_stamped_punches", lambda: _section("skip_stamps", _plan_skip_stamps(win)))
	run("d_mirrored_absent_rows", lambda: _section("mirrored_rows", _plan_mirrored_rows(win)))
	run("e_late_checkout_still_broken", lambda: _section("rebuild", _late_checkouts(win)))
	run("f_missing_erp_punches", missing)
	run("g_overwritten_punches", lambda: _section("overwritten", _plan_overwritten(win)))
	run("h_days_after_today", excluded)

	def ot_requests():
		review = _ot_request_review(win)
		logger.info(
			"[attendance_recovery] section i: %d OT request(s) priced below claim", len(review["hr_list"])
		)
		return {
			"fix": None,
			"note": "pre-deploy check, read-only: HR re-dates or amends these requests",
			"count": len(review["hr_list"]),
			"checked": review["checked"],
			"overtime_pay": len(review["overtime_pay"]),
			"replacement_leave": len(review["replacement_leave"]),
			"sample": review["overtime_pay"][:SAMPLE],
			"hr_sample": review["replacement_leave"][:SAMPLE],
		}

	run("i_ot_requests_priced_below_claim", ot_requests)
	logger.info(
		"[attendance_recovery] inputs report %s..%s by %s: %s",
		win.start,
		win.end,
		frappe.session.user,
		{k: v.get("count", v.get("error")) for k, v in sections.items()},
	)
	return {"from_date": str(win.start), "to_date": str(win.end), "order": list(STEPS), "sections": sections}


@frappe.whitelist()
def hr_list(from_date=str(REPAIR_FLOOR), to_date=None, include_source=0) -> dict:
	"""Days no step can fix, with a plain reason, for HR to correct the master data. Read-only."""
	_require_operator("read attendance inputs across every company")
	win = _window(from_date, to_date)
	rows, errors = [], {}
	for step in STEPS:
		if step == "import" and not cint(include_source):
			continue
		try:
			plan = _PLANNERS[step](win, for_update=False)
		except Exception as exc:
			if _lost_transaction(exc):
				raise
			logger.exception("[attendance_recovery] hr_list could not plan %s", step)
			errors[step] = str(exc)
			continue
		rows.extend({**h, "step": step} for h in plan.get("hr_list") or [])
	try:
		rows.extend({**h, "step": "ot_requests"} for h in _ot_request_review(win)["hr_list"])
	except Exception as exc:
		if _lost_transaction(exc):
			raise
		logger.exception("[attendance_recovery] hr_list could not review OT requests")
		errors["ot_requests"] = str(exc)
	rows.sort(key=lambda h: (str(h.get("employee")), str(h.get("date")), h["step"]))
	logger.info(
		"[attendance_recovery] hr_list %s..%s: %d row(s), errors %s", win.start, win.end, len(rows), errors
	)
	return {"from_date": str(win.start), "to_date": str(win.end), "rows": rows, "errors": errors}
