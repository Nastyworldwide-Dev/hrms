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

0. release_mirrored  broken days still stamped as the ERP's copy become Verifica's
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

Mirrored broken days (step 0, inputs_report section j): rows copied from the
ERP before cutover keep `synced_from_instance`, and every automation path
skips a stamped row, so a broken August day copied from the ERP was invisible
to every step below. Verifica owns its data since cutover (owner ruling 14 Sep
2026), so for exactly the broken, unprotected days the stamp is cleared —
nothing deleted or cancelled, links kept — and `rebuild` then re-marks those
days (`_remark_released_day`). Healthy mirrored days keep their stamp.

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
from itertools import pairwise

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from hrms.overrides.company_scope import require_unfenced
from hrms.sync.write_block import PROVENANCE_FIELD
from hrms.utils import hr_removed_day
from hrms.utils.dry_run import wants_dry_run
from hrms.utils.offshift_punch_heal import _lost_transaction

logger = logging.getLogger(__name__)

#: Owner ruling: OT stays claimable four cycles back, so repair starts here.
REPAIR_FLOOR = date(2026, 8, 1)
#: unlock_mirrored_writes day. Before it the source ERP owned attendance.
CUTOVER = date(2026, 9, 4)
MAX_WINDOW_DAYS = 62
STEPS = (
	"release_mirrored",
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
#: The Comment on every row `release_mirrored` released; the rebuild step finds released days by it.
RELEASE_NOTE = "Released from ERP copy by attendance recovery (Verifica owns this day)"
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


def protected_reason(day, today: date, rows, financial=None, removed_by_hr=False) -> str | None:
	"""Why this employee-day must not be rebuilt, or None. Pure.

	`rows` are the day's Attendance rows (any docstatus); `financial` is what
	`_repair_financial_dependency` returned for the day; `removed_by_hr` is
	whether HR removed the day in Shift Attendance (hrms.utils.hr_removed_day).
	"""
	day = getdate(day)
	if day >= today:
		return "today or later: never touched"
	if removed_by_hr:
		# Group 2-4 review C1: the removal leaves no row, so only the marker says who owns it.
		return "removed by HR in Shift Attendance: HR hands it back first"
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
	return protected_reason(
		day,
		_today(),
		rows,
		_financial(employee, day, rows, for_update),
		removed_by_hr=hr_removed_day.removed_by_hr(employee, day),
	)


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


# --- 0. release mirrored broken days -------------------------------------------------


def mirrored_day_problems(rows, punches) -> list[tuple[str, str]]:
	"""Why one employee-day of ERP-copied data looks broken: [(shape, text)]. Pure.

	Empty when the day is healthy or holds no mirrored row at all. `rows`: the
	day's Attendance (any docstatus, mirrored or not); `punches`: its
	non-rejected punches, mirrored or local, on that shift day.
	"""
	submitted = [r for r in rows if cint(r.get("docstatus")) == 1]
	mirrored_rows = [r for r in submitted if r.get(PROVENANCE_FIELD)]
	mirrored_punch = any(p.get(PROVENANCE_FIELD) for p in punches)
	if not punches or not (mirrored_rows or mirrored_punch):
		return []
	count = len(punches)
	if not submitted:
		return [("no_attendance", f"{count} punch(es) and no submitted attendance")] if mirrored_punch else []
	types = {p.get("log_type") for p in punches}
	one_sided = next(iter(types)) if len(types) == 1 and types <= {"IN", "OUT"} else None
	problems = []
	for row in mirrored_rows:
		hours = flt(row.get("working_hours"))
		label = f"mirrored {row.get('status')} {row.get('name')}"
		if row.get("status") in ("Absent", "Half Day") or not hours:
			problems.append(("broken_row", f"{label} ({hours} h) on a day with {count} punch(es)"))
		elif count % 2 or one_sided:
			shape = f"all {one_sided}" if one_sided else "an odd number"
			problems.append(("unpaired_punches", f"{label} over {count} punch(es), {shape}"))
	return problems


def _plan_release_mirrored(win, for_update=False) -> dict:
	"""Section j and step `release_mirrored`: broken days that are still the ERP's copy.

	One Attendance read and one Employee Checkin read for the window. A day is
	listed only when `mirrored_day_problems` finds it broken and
	`protected_reason` finds nothing (today, HR-kept, leave, Attendance Request,
	half-day leave, HR-removed, paid); a protected day goes to held_back.
	"""
	rows = frappe.get_all(
		"Attendance",
		filters={"attendance_date": ["between", [win.start, win.end]], "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
		limit_page_length=0,
	)
	punches = frappe.get_all(
		"Employee Checkin",
		filters=[
			["time", ">=", datetime.combine(win.start - timedelta(days=1), time.min)],
			["time", "<", datetime.combine(win.end + timedelta(days=2), time.min)],
		],
		fields=[
			"name",
			"employee",
			"time",
			"log_type",
			"shift_start",
			"attendance",
			PROVENANCE_FIELD,
			"remote_approval_status",
		],
		limit_page_length=0,
	)
	days = {}
	for row in rows:
		day = getdate(row.get("attendance_date"))
		if win.start <= day <= win.end:
			days.setdefault((row.get("employee"), day), ([], []))[0].append(row)
	for punch in punches:
		day = getdate(punch.get("shift_start") or punch.get("time"))
		if win.start <= day <= win.end:
			days.setdefault((punch.get("employee"), day), ([], []))[1].append(punch)

	today, planned, held, shapes = _today(), [], [], Counter()
	for (employee, day), (day_rows, day_punches) in sorted(
		days.items(), key=lambda i: (str(i[0][0]), i[0][1])
	):
		kept = [p for p in day_punches if p.get("remote_approval_status") != "Rejected"]
		problems = mirrored_day_problems(day_rows, kept)
		if not problems:
			continue
		stamped_rows = [r for r in day_rows if cint(r.get("docstatus")) == 1 and r.get(PROVENANCE_FIELD)]
		first = stamped_rows[0] if stamped_rows else {}
		entry = {
			"employee": employee,
			"date": str(day),
			"attendance": first.get("name"),
			"status": first.get("status"),
			"working_hours": flt(first.get("working_hours")) if first else None,
			"punch_count": len(kept),
			"problem": "; ".join(text for _shape, text in problems),
			"shapes": [shape for shape, _text in problems],
			"release_checkins": sorted(p.get("name") for p in day_punches if p.get(PROVENANCE_FIELD)),
			"release_attendance": sorted(r.get("name") for r in stamped_rows),
		}
		reason = protected_reason(day, today, day_rows) or protected_reason(
			day,
			today,
			day_rows,
			_financial(employee, day, day_rows, for_update),
			removed_by_hr=hr_removed_day.removed_by_hr(employee, day),
		)
		if reason:
			held.append(_held(entry, reason))
			continue
		planned.append(entry)
		shapes.update(entry["shapes"])
	logger.info(
		"[attendance_recovery] mirrored broken days %s..%s: %d to release, %d held, shapes %s",
		win.start,
		win.end,
		len(planned),
		len(held),
		dict(shapes),
	)
	return _outcome(planned, held, employees=len({p["employee"] for p in planned}), shapes=dict(shapes))


def _release_day(entry, win) -> dict:
	"""Clear the ERP stamp on one listed day's rows, with one Comment on each.

	Deletes nothing, cancels nothing, and keeps every punch's `attendance` link.
	`frappe.db.set_value` (as `purge.release_instance_stamp`) because the
	write-block's validate hook would put the stamp back on a saved document.

	What the hourly job then does (ShiftType.get_employee_checkins reads punches
	with this shift, attendance not set, no stamp, time >= process_attendance_after
	and shift_actual_end < last_sync_of_checkin): a released punch that is still
	LINKED is never read by it — only the `rebuild` step re-marks that day. A
	released punch that was UNLINKED becomes readable, so if the shift's
	process_attendance_after is on or before that day the next hourly run marks
	it with the same engine rule `rebuild` uses; only the listed (unprotected)
	days can be reached that way, never a healthy mirrored day. The absent sweep
	already counted mirrored punches as punched, so it changes nothing. After
	cutover the sync never pulls Attendance again, and the punch import matches
	(employee, time, log_type), so a released punch is not re-imported.
	"""
	day = getdate(entry["date"])
	if day > win.end:
		raise frappe.ValidationError(f"{day} is today or later")
	released = []
	for doctype, key in (("Employee Checkin", "release_checkins"), ("Attendance", "release_attendance")):
		for name in entry.get(key) or []:
			frappe.db.set_value(doctype, name, PROVENANCE_FIELD, None, update_modified=False)
			frappe.get_doc(
				{
					"doctype": "Comment",
					"comment_type": "Comment",
					"reference_doctype": doctype,
					"reference_name": name,
					"content": RELEASE_NOTE,
				}
			).insert(ignore_permissions=True)
			released.append(name)
	logger.info(
		"[attendance_recovery] released %s on %s from the ERP copy: %s", entry["employee"], day, released
	)
	return {"employee": entry["employee"], "date": str(day), "released": released}


def _apply_release_mirrored(win, plan) -> dict:
	done, held = [], []
	for entry in plan["planned"]:
		result, error = _guarded(
			f"release {entry['employee']} {entry['date']}", lambda entry=entry: _release_day(entry, win)
		)
		if error:
			held.append(_held(entry, f"could not be released: {error}", hr=False))
		else:
			done.append(result)
	logger.info("[attendance_recovery] release: %d day(s) released, %d held", len(done), len(held))
	return {"done": done, "held_back": held}


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


def _editor_assignments(names) -> set:
	"""Which of these Shift Assignments the Shift Attendance editor created
	(attendance_master_edit._ensure_assignment comments every one)."""
	if not names:
		return set()
	found = set(
		frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Shift Assignment",
				"reference_name": ["in", sorted(names)],
				"content": ["like", "%via Shift Attendance%"],
			},
			pluck="reference_name",
		)
	)
	logger.debug("[attendance_recovery] %d of %d assignment(s) made by the editor", len(found), len(names))
	return found


def _plan_assignments(win, for_update=False) -> dict:
	"""Night assignments overlapping a day assignment; planned only when never
	used, ending by today, and not HR's own one-day assignment from the editor."""
	rows = _submitted_assignments(win.start, win.end)
	times = _shift_times({r.shift_type for r in rows})
	night_types = {name for name, (start, end) in times.items() if is_night_shift(start, end)}
	editor_made = _editor_assignments({r.name for r in rows if r.shift_type in night_types})
	today = _today()
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
			if night.name in editor_made:
				held.append(_held(entry, "created by HR in Shift Attendance: never ended here", hr=False))
				continue
			if not night.end_date or getdate(night.end_date) > today:
				# Group 2-4 review W8: ending it at yesterday would drop a future rotation.
				# ceiling: an unused past with a future range always goes to HR, upgrade:
				# end only the past part (split the assignment) if HR's list grows too long
				held.append(
					_held(
						entry, "future range — HR to end: the assignment runs past today or has no end date"
					)
				)
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


def _released_days(win) -> set:
	"""(employee, day) in the window that `release_mirrored` released, found by its Comment."""
	# ceiling: every released row's Comment is read each run, upgrade: store the
	# release date on the Comment and filter by it if releases reach tens of thousands
	comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": ["in", ["Attendance", "Employee Checkin"]], "content": RELEASE_NOTE},
		fields=["reference_doctype", "reference_name"],
		limit_page_length=0,
	)
	names = {"Attendance": set(), "Employee Checkin": set()}
	for comment in comments:
		if comment.get("reference_doctype") in names:
			names[comment["reference_doctype"]].add(comment.get("reference_name"))
	days = set()
	if names["Attendance"]:
		for row in frappe.get_all(
			"Attendance",
			filters={
				"name": ["in", sorted(names["Attendance"])],
				"docstatus": 1,
				"attendance_date": ["between", [win.start, win.end]],
			},
			fields=["employee", "attendance_date"],
			limit_page_length=0,
		):
			days.add((row.employee, getdate(row.attendance_date)))
	if names["Employee Checkin"]:
		for punch in frappe.get_all(
			"Employee Checkin",
			filters={"name": ["in", sorted(names["Employee Checkin"])]},
			fields=["employee", "time", "shift_start"],
			limit_page_length=0,
		):
			day = getdate(punch.shift_start or punch.time)
			if win.start <= day <= win.end:
				days.add((punch.employee, day))
	logger.debug("[attendance_recovery] %d released day(s) in %s..%s", len(days), win.start, win.end)
	return days


def _same_result(result, shift_name) -> bool:
	from hrms.hr.doctype.employee_checkin.employee_checkin import _same_day_result

	return _same_day_result(
		result.existing,
		result.status,
		result.working_hours,
		result.get("in_time"),
		result.get("out_time"),
		shift_name,
	)


def _remark_released_day(employee, day, apply) -> dict:
	"""The engine's own marking for a released day, whose punches may all still be linked.

	`checkin_import._remark_day` reads only unlinked punches, so a day whose ERP
	copy linked every punch to its Absent row would read "up to date" forever.
	Here the day's punches are: unlinked, linked to this day's submitted row, or
	linked to a row that is not submitted anywhere (a link the ERP copy left
	dangling). `ShiftType.mark_attendance_for_shift_logs` then keeps the row when
	the result is the same, or cancels and re-marks it from all of them.
	"""
	from hrms.hr.doctype.shift_type.shift_type import CHECKIN_FIELDS

	day = getdate(day)
	start = datetime.combine(day, time.min)
	punches = frappe.get_all(
		"Employee Checkin",
		filters=[
			["employee", "=", employee],
			["shift_start", ">=", start],
			["shift_start", "<", start + timedelta(days=1)],
			["shift", "is", "set"],
			[PROVENANCE_FIELD, "is", "not set"],
		],
		fields=list(CHECKIN_FIELDS),
		order_by="time asc",
		limit_page_length=0,
	)
	links = sorted({p.get("attendance") for p in punches if p.get("attendance")})
	submitted = {}
	if links:
		for row in frappe.get_all(
			"Attendance",
			filters={"name": ["in", links], "docstatus": 1},
			fields=["name", "attendance_date"],
			limit_page_length=0,
		):
			submitted[row.name] = getdate(row.attendance_date)
	by_shift = {}
	for punch in punches:
		if cint(punch.get("skip_auto_attendance")):
			continue
		if punch.get("attendance") and submitted.get(punch.get("attendance"), day) != day:
			continue  # linked to another day's row
		by_shift.setdefault(punch.get("shift"), []).append(punch)

	changed, expected, marked, errors = False, [], [], []
	for shift_name, logs in sorted(by_shift.items()):
		shift = frappe.get_doc("Shift Type", shift_name)
		result = shift.shift_day_result(employee, day, logs)
		if not result:
			expected.append(
				{"shift": shift_name, "status": None, "detail": "the shift's rules would not mark this day"}
			)
			continue
		existing = result.get("existing")
		same = (
			bool(existing)
			and all(p.get("attendance") == existing.name for p in result.eligible_logs)
			and _same_result(result, shift_name)
		)
		expected.append(
			{
				"shift": shift_name,
				"status": result.status,
				"working_hours": round(flt(result.working_hours), 2),
				"rebuilds": existing.name if existing else None,
				"unchanged": same,
			}
		)
		if same:
			continue
		changed = True
		if not apply:
			continue
		if shift.has_incorrect_shift_config():
			errors.append(f"{shift_name}: auto attendance is off or not configured")
			continue
		doc = shift.mark_attendance_for_shift_logs(employee, day, logs)
		if doc:
			marked.append(doc.name)
		else:
			errors.append(f"{shift_name}: the shift's rules did not mark this day")
	logger.info(
		"[attendance_recovery] released day %s %s: changed=%s marked=%s errors=%s",
		employee,
		day,
		changed,
		marked,
		errors,
	)
	return {"changed": changed, "expected": expected, "marked": marked, "errors": errors}


def _plan_rebuild(win, for_update=False) -> dict:
	"""Days holding punches the engine would read (shift set, unlinked, not skipped),
	and days `release_mirrored` released whose engine result would change."""
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
	released = _released_days(win)
	days = sorted(
		{(r.employee, getdate(r.shift_start)) for r in rows} | released, key=lambda d: (str(d[0]), d[1])
	)
	planned, held = [], []
	for employee, day in days:
		if not (win.start <= day <= win.end):
			continue
		entry = {"employee": employee, "date": str(day)}
		reason = _day_protection(employee, day, for_update)
		if reason:
			held.append(_held(entry, reason))
			continue
		if (employee, day) in released:
			preview = _remark_released_day(employee, day, False)
			expected = preview.get("expected") or []
			if preview.get("changed"):
				planned.append({**entry, "expected": expected, "released": True})
			elif expected and not any(e.get("status") for e in expected):
				held.append(_held(entry, "the engine would not mark this released day"))
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
	remark = _remark_released_day if entry.get("released") else _remark_day
	result = remark(entry["employee"], day, True) or {}
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
	"release_mirrored": _plan_release_mirrored,
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
	"release_mirrored": _apply_release_mirrored,
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


def _section(fix, plan, family=None) -> dict:
	"""One inputs_report section. Every section carries the E34 split: count_fixable
	(planned) + count_on_purpose (held, protected) + count_needs_hr (held, HR's) = detected."""
	planned = plan.get("planned") or []
	held = plan.get("held_back") or []
	return {
		"fix": fix,
		**({"family": family} if family else {}),
		"count": _planned_count(plan),
		"days": len({(p.get("employee"), str(p.get("date"))) for p in planned}),
		"held_back": len(held),
		"hr_list": len(plan.get("hr_list") or []),
		**_counts(_planned_count(plan), held),
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
		reason = protected_reason(
			day,
			_today(),
			rows,
			_financial(request.employee, day, rows, False),
			removed_by_hr=hr_removed_day.removed_by_hr(request.employee, day),
		)
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
			return {
				"fix": "import",
				"note": "not read: pass include_source=1 (bench execute)",
				**_counts(0, []),
			}
		instance = _source_instance()
		if not instance:
			return {
				"fix": "import",
				"note": "no single enabled ERP instance with credentials",
				**_counts(0, []),
			}
		from hrms.sync.missing_checkins import report

		found = report(instance=instance, from_date=str(win.start), to_date=str(win.end), sample=SAMPLE)
		return {
			**_section("import", _plan_import(win)),
			"missing": found.get("missing"),
			"type_mismatch": found.get("type_mismatch"),
		}

	def excluded():
		if not win.excluded_from:
			return {"fix": None, "count": 0, **_counts(0, [])}
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
			**_counts(0, []),
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
			**_counts(0, review["hr_list"]),
			"checked": review["checked"],
			"overtime_pay": len(review["overtime_pay"]),
			"replacement_leave": len(review["replacement_leave"]),
			"sample": review["overtime_pay"][:SAMPLE],
			"hr_sample": review["replacement_leave"][:SAMPLE],
		}

	run("i_ot_requests_priced_below_claim", ot_requests)

	def mirrored():
		plan = _plan_release_mirrored(win)
		logger.info("[attendance_recovery] section j: %d mirrored broken day(s)", len(plan["planned"]))
		return {
			**_section("release_mirrored", plan),
			"employees": plan.get("employees", 0),
			"shapes": plan.get("shapes", {}),
		}

	run("j_mirrored_broken_days", mirrored)

	# S1 (15 Sep 2026): the read-only detectors, one context read shared by all seven.
	ctx = {}

	def detector(family, fix, planner):
		def read():
			if not ctx:
				ctx["value"] = _context(win)
			return _section(fix, globals()[planner](win, ctx=ctx["value"]), family)

		return read

	for family, key, fix, planner in UNCLAIMABLE_FAMILIES:
		run(key, detector(family, fix, planner))
	run(CONFIG_SECTION, _config_section)
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


# --- unclaimable days: read-only detectors (S1) ---------------------------------------------------------
#
# Nabil's rule (15 Sep 2026): the session runs from an IN to the next tap (<= 20 h),
# whatever that tap is labelled; it belongs to the shift the person is ROSTERED on
# that day; shift config is HR's (reported, never edited); a legit Half Day / leave /
# Attendance Request is not broken. Every planner below is a read: it returns the
# same {"planned", "held_back", "hr_list"} shape as the steps, but nothing here
# is ever applied. `planned` = a recovery step (existing or planned) could fix
# it; `held_back` with a protected reason = left alone on purpose; any other
# `held_back` = only HR can fix it (`attendance_auto_recovery.needs_hr`).

#: A tap this many hours after an open IN still closes that IN's session.
SESSION_HOURS = 20
#: A pending late-checkout request older than this: the approver never acted.
LATE_CHECKOUT_STALE_DAYS = 3
#: hr_list wording for a lone IN (owner ruling: never auto-closed).
LONE_IN = "lone IN: no closing tap within 20 h — HR closes the day in Shift Attendance"
#: Fix labels for the families whose fixer is a later slice, not a step yet.
ROSTERED_SHIFT_FIX = "rostered_shift"
LATE_CHECKOUT_FIX = "late_checkout"
#: family -> (inputs_report section, the step that fixes a planned row or None, planner name)
UNCLAIMABLE_FAMILIES = (
	("F1", "k_wrong_shift_taps", ROSTERED_SHIFT_FIX, "_plan_wrong_shift_taps"),
	("F2", "l_lone_in", None, "_plan_lone_in"),
	("F4", "m_out_first_or_double_out", None, "_plan_out_first"),
	("F6", "n_no_attendance_row", "rebuild", "_plan_no_attendance_row"),
	("F7", "o_skipped_taps", "skip_stamps", "_plan_skipped_taps"),
	("F9", "p_late_checkout_requests", LATE_CHECKOUT_FIX, "_plan_late_checkout_requests"),
	("F13", "q_present_without_live_taps", "rebuild", "_plan_present_without_live_taps"),
)
CONFIG_SECTION = "r_config_health"
BUFFER_WARN_MINUTES = 120
ALTERNATING = "Alternating entries as IN and OUT during the same shift"
FIRST_LAST = "First Check-in and Last Check-out"
STATUS_FIXABLE, STATUS_ON_PURPOSE, STATUS_NEEDS_HR = "fixable", "on purpose", "needs HR"


def _segments(start_time, end_time) -> list:
	"""Minute segments of a scheduled shift on one 24 h clock; two when it crosses midnight."""
	start, end = _minutes(start_time), _minutes(end_time)
	if start <= end:
		return [(start, end)]
	return [(start, 24 * 60), (0, end)]


def shifts_overlap(a, b) -> bool:
	"""Do two shifts' SCHEDULED hours (start, end) share a minute? Buffers left out. Pure.

	This is how a "night" shift is recognised here — by overlapping the day shift,
	not by ending before 06:00 (a 19:30-07:00 shift is night in every sense that
	matters and `is_night_shift` never saw it).
	"""
	return any(s1 < e2 and s2 < e1 for s1, e1 in _segments(*a) for s2, e2 in _segments(*b))


def session_days(taps) -> dict:
	"""{tap name: the day its session belongs to}. Pure.

	A tap within SESSION_HOURS after an open IN closes that IN, whatever its
	label, and belongs to the IN's clock day (a 07:00 tap after a 19:30 IN is
	the night session's OUT). Anything else starts on its own clock day; only
	an IN opens a session.
	"""
	anchors, open_in = {}, None
	for tap in sorted(taps, key=lambda t: get_datetime(t["time"])):
		moment = get_datetime(tap["time"])
		if open_in and moment - open_in[0] <= timedelta(hours=SESSION_HOURS):
			anchors[tap["name"]] = open_in[1]
			open_in = None
			continue
		anchors[tap["name"]] = moment.date()
		open_in = (moment, moment.date()) if tap.get("log_type") == "IN" else None
	return anchors


def day_shape(taps) -> str | None:
	"""'lone-in' | 'lone-out' | 'out-first' | 'double-out' | None for one day's taps. Pure."""
	taps = sorted(taps, key=lambda t: get_datetime(t["time"]))
	if not taps:
		return None
	if len(taps) == 1:
		return "lone-in" if taps[0].get("log_type") == "IN" else "lone-out"
	if taps[0].get("log_type") == "OUT":
		return "out-first"
	if any(a.get("log_type") == "OUT" and b.get("log_type") == "OUT" for a, b in pairwise(taps)):
		return "double-out"
	return None


def only_closer(day_taps, tap) -> bool:
	"""Is this skipped tap the only thing that could close a lone IN that day? Pure.

	`day_taps`: every non-rejected tap of the session day, the skipped one included.
	"""
	live = [
		t
		for t in day_taps
		if not cint(t.get("skip_auto_attendance")) and t.get("remote_approval_status") != "Rejected"
	]
	return (
		len(live) == 1
		and live[0].get("log_type") == "IN"
		and get_datetime(tap["time"]) > get_datetime(live[0]["time"])
	)


def _needs_hr(held) -> bool:
	# Lazy: attendance_auto_recovery imports this module at load time.
	from hrms.utils.attendance_auto_recovery import needs_hr

	return needs_hr(held)


def row_status(row, held: bool) -> str:
	"""fixable (a step fixes it) | on purpose (protected) | needs HR."""
	if not held:
		return STATUS_FIXABLE
	return STATUS_NEEDS_HR if _needs_hr(row) else STATUS_ON_PURPOSE


def _counts(count, held) -> dict:
	"""E34: count_fixable + count_on_purpose + count_needs_hr = detected, for one section."""
	needs = sum(1 for h in held if _needs_hr(h))
	return {"count_fixable": count, "count_needs_hr": needs, "count_on_purpose": len(held) - needs}


def family_counts(rows) -> dict:
	"""{family: {detected, fixable, on_purpose, needs_hr}} over `unclaimable_rows` output. Pure."""
	out = {}
	keys = {STATUS_FIXABLE: "fixable", STATUS_ON_PURPOSE: "on_purpose"}
	for row in rows:
		tally = out.setdefault(
			row.get("family"), {"detected": 0, "fixable": 0, "on_purpose": 0, "needs_hr": 0}
		)
		tally["detected"] += 1
		tally[keys.get(row.get("status"), "needs_hr")] += 1
	return out


def _unclaimable(family, employee, day, reason, **extra) -> dict:
	return {
		"family": family,
		"employee": employee,
		"employee_name": extra.pop("employee_name", None),
		"date": str(day),
		"reason": reason,
		"shift": extra.pop("shift", None),
		"attendance": extra.pop("attendance", None),
		"status": extra.pop("status", None),
		"taps": extra.pop("taps", 0),
		**extra,
	}


def _context(win) -> dict:
	"""The window's taps, attendance rows and assignments, read once for every detector."""
	taps = frappe.get_all(
		"Employee Checkin",
		filters=[
			["time", ">=", datetime.combine(win.start - timedelta(days=1), time.min)],
			["time", "<", datetime.combine(win.end + timedelta(days=2), time.min)],
		],
		fields=[
			"name",
			"employee",
			"employee_name",
			"time",
			"log_type",
			"shift",
			"shift_start",
			"attendance",
			"skip_auto_attendance",
			"remote_approval_status",
			PROVENANCE_FIELD,
		],
		order_by="employee asc, time asc",
		limit_page_length=0,
	)
	rows = frappe.get_all(
		"Attendance",
		filters={"attendance_date": ["between", [win.start, win.end]], "docstatus": ["<", 2]},
		fields=[*ATTENDANCE_FIELDS, "shift", "employee_name", "in_time"],
		limit_page_length=0,
	)
	assignments = _submitted_assignments(win.start, win.end)
	return _build_context(win, taps, rows, assignments)


def _build_context(win, taps, rows, assignments) -> dict:
	"""Group what `_context` read; separate so a test can hand in plain rows."""
	by_employee, anchors = {}, {}
	for tap in taps:
		by_employee.setdefault(tap.get("employee"), []).append(tap)
	for own in by_employee.values():
		anchors.update(session_days([t for t in own if t.get("remote_approval_status") != "Rejected"]))
	days = {}
	for tap in taps:
		if tap.get("remote_approval_status") == "Rejected":
			continue
		day = anchors.get(tap.get("name")) or getdate(tap.get("time"))
		days.setdefault((tap.get("employee"), day), []).append(tap)
	rows_by_day = {}
	for row in rows:
		rows_by_day.setdefault((row.get("employee"), getdate(row.get("attendance_date"))), []).append(row)
	assigned = {}
	for assignment in assignments:
		assigned.setdefault(assignment.get("employee"), []).append(assignment)
	ctx = {
		"taps": taps,
		"anchors": anchors,
		"days": days,  # (employee, session day) -> that day's non-rejected taps
		"rows": rows,
		"rows_by_day": rows_by_day,
		"assignments": assigned,
		"times": _shift_times(
			{a.get("shift_type") for a in assignments} | {r.get("shift") for r in rows if r.get("shift")}
		),
	}
	logger.info(
		"[attendance_recovery] unclaimable context %s..%s: %d tap(s), %d row(s), %d assignment(s)",
		win.start,
		win.end,
		len(taps),
		len(rows),
		len(assignments),
	)
	return ctx


def _covering(ctx, employee, day) -> list:
	return [
		a
		for a in ctx["assignments"].get(employee, [])
		if getdate(a.get("start_date")) <= day
		and (not a.get("end_date") or getdate(a.get("end_date")) >= day)
	]


def _protection(ctx, employee, day, for_update) -> str | None:
	"""Cheap check on the rows already read, then the full one (financial, HR-removed)."""
	quick = protected_reason(day, _today(), ctx["rows_by_day"].get((employee, day), []))
	return quick or _day_protection(employee, day, for_update)


def _live_row(ctx, employee, day):
	return next(
		(r for r in ctx["rows_by_day"].get((employee, day), []) if cint(r.get("docstatus")) == 1), None
	)


def _in_window(win, day) -> bool:
	return win.start <= day <= win.end


def _sorted_days(ctx):
	return sorted(ctx["days"].items(), key=lambda i: (str(i[0][0]), i[0][1]))


def _plan_wrong_shift_taps(win, for_update=False, ctx=None) -> dict:
	"""F1: a session-day whose taps carry a shift the employee is not rostered on that
	day (fixable: re-stamp to the rostered shift), and two Active assignments whose
	SCHEDULED hours overlap (HR ends one, or keeps both on purpose)."""
	ctx = ctx or _context(win)
	times, planned, held, overlapping = ctx["times"], [], [], {}
	for employee, assignments in sorted(ctx["assignments"].items()):
		for i, a in enumerate(assignments):
			for b in assignments[i + 1 :]:
				if a.shift_type == b.shift_type or a.shift_type not in times or b.shift_type not in times:
					continue
				span = _overlap(a, [b], win)
				if not span or not shifts_overlap(times[a.shift_type], times[b.shift_type]):
					continue
				overlapping.setdefault(employee, []).append(span)
				entry = _unclaimable(
					"F1",
					employee,
					span[0],
					None,
					shift=f"{a.shift_type} + {b.shift_type}",
					to_date=str(span[1]),
					assignments=[a.name, b.name],
				)
				held.append(
					_held(
						entry,
						f"two Active assignments overlap by scheduled hours until {span[1]} "
						f"({a.name} {a.shift_type}, {b.name} {b.shift_type}): HR ends one or keeps both on purpose",
					)
				)
	for (employee, day), taps in _sorted_days(ctx):
		if not _in_window(win, day):
			continue
		rostered = sorted({a.shift_type for a in _covering(ctx, employee, day)})
		if not rostered:
			continue  # shiftless: section b's family
		if any(s <= day <= e for s, e in overlapping.get(employee, [])):
			continue  # listed above: the roster itself is ambiguous
		stamps = sorted({t.shift for t in taps if t.shift})
		wrong = sorted(set(stamps) - set(rostered))
		if not wrong and len(stamps) < 2:
			continue
		# One session, one shift (Nabil): a session whose taps carry two stamps was
		# split by a buffer window (Ria's 19:30 tap on a day-shift session).
		what = (
			f"session split across {', '.join(stamps)}"
			if len(stamps) > 1
			else f"tap(s) stamped to {', '.join(wrong)}"
		)
		row = _live_row(ctx, employee, day)
		entry = _unclaimable(
			"F1",
			employee,
			day,
			f"{what}; rostered on {', '.join(rostered)}",
			employee_name=taps[0].employee_name,
			shift=", ".join(stamps),
			rostered=rostered,
			attendance=row and row.name,
			status=row and row.status,
			taps=len(taps),
		)
		reason = _protection(ctx, employee, day, for_update)
		if reason:
			held.append(_held(entry, reason))
		elif len(rostered) > 1:
			held.append(
				_held(
					entry,
					f"{what}; two shifts rostered that day ({', '.join(rostered)}): "
					"HR ends one assignment or keeps both on purpose",
				)
			)
		else:
			planned.append(entry)
	logger.info(
		"[attendance_recovery] F1 %s..%s: %d to re-stamp, %d held",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _plan_lone_in(win, for_update=False, ctx=None) -> dict:
	"""F2: a session-day with exactly one non-rejected tap, typed IN. Never auto-closed."""
	ctx = ctx or _context(win)
	held = []
	for (employee, day), taps in _sorted_days(ctx):
		if not _in_window(win, day) or day_shape(taps) != "lone-in":
			continue
		row = _live_row(ctx, employee, day)
		entry = _unclaimable(
			"F2",
			employee,
			day,
			None,
			employee_name=taps[0].employee_name,
			shift=taps[0].shift,
			attendance=row and row.name,
			status=row and row.status,
			taps=1,
			checkin=taps[0].name,
			time=str(taps[0].time),
		)
		held.append(_held(entry, _protection(ctx, employee, day, for_update) or LONE_IN))
	logger.info("[attendance_recovery] F2 %s..%s: %d lone IN(s)", win.start, win.end, len(held))
	return _outcome([], held)


def _plan_out_first(win, for_update=False, ctx=None) -> dict:
	"""F4: first tap typed OUT, or two OUTs in a row (the engine's alternating pairing
	already reads them; informational), and an OUT with no IN at all (HR)."""
	ctx = ctx or _context(win)
	planned, held = [], []
	for (employee, day), taps in _sorted_days(ctx):
		shape = day_shape(taps)
		if not _in_window(win, day) or shape not in ("lone-out", "out-first", "double-out"):
			continue
		row = _live_row(ctx, employee, day)
		entry = _unclaimable(
			"F4",
			employee,
			day,
			None,
			employee_name=taps[0].employee_name,
			shift=taps[0].shift,
			attendance=row and row.name,
			status=row and row.status,
			taps=len(taps),
			shape=shape,
		)
		if shape == "lone-out":
			reason = _protection(ctx, employee, day, for_update) or "OUT with no IN: HR keys the IN"
			held.append(_held(entry, reason))
		else:
			text = "first tap typed OUT" if shape == "out-first" else "two OUTs in a row"
			planned.append(
				{**entry, "reason": f"{text}: alternating pairing reads it as the session's IN/OUT"}
			)
	logger.info(
		"[attendance_recovery] F4 %s..%s: %d informational, %d held",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _holiday_days(employees, win) -> set:
	"""(employee, date) pairs that are holidays for that employee in the window."""
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	lists = {}
	for employee in sorted(employees):
		try:
			lists[employee] = get_holiday_list_for_employee(employee, raise_exception=False, as_on=win.end)
		except Exception:
			logger.exception("[attendance_recovery] holiday list of %s unreadable", employee)
	names = sorted({v for v in lists.values() if v})
	if not names:
		return set()
	holidays = frappe.get_all(
		"Holiday",
		filters={"parent": ["in", names], "holiday_date": ["between", [win.start, win.end]]},
		fields=["parent", "holiday_date"],
		limit_page_length=0,
	)
	dated = {(h.parent, getdate(h.holiday_date)) for h in holidays}
	return {(e, d) for e, name in lists.items() for (n, d) in dated if n == name}


def _plan_no_attendance_row(win, for_update=False, ctx=None) -> dict:
	"""F6: a rostered working day with two or more live taps and no Attendance row at all."""
	ctx = ctx or _context(win)
	candidates = []
	for (employee, day), taps in _sorted_days(ctx):
		live = [t for t in taps if not cint(t.get("skip_auto_attendance"))]
		if not _in_window(win, day) or len(live) < 2 or ctx["rows_by_day"].get((employee, day)):
			continue
		covering = _covering(ctx, employee, day)
		if covering:
			candidates.append((employee, day, live, covering))
	holidays = _holiday_days({c[0] for c in candidates}, win)
	planned, held = [], []
	for employee, day, live, covering in candidates:
		if (employee, day) in holidays:
			continue
		rostered = ", ".join(sorted({a.shift_type for a in covering}))
		entry = _unclaimable(
			"F6",
			employee,
			day,
			f"{len(live)} tap(s), rostered on {rostered}, no attendance row",
			employee_name=live[0].employee_name,
			shift=live[0].shift,
			taps=len(live),
		)
		reason = _protection(ctx, employee, day, for_update)
		(held.append(_held(entry, reason)) if reason else planned.append(entry))
	logger.info(
		"[attendance_recovery] F6 %s..%s: %d to rebuild, %d held", win.start, win.end, len(planned), len(held)
	)
	return _outcome(planned, held)


def _skip_reasons(names) -> dict:
	from hrms.utils.attendance_day_audit import SKIP_PREFIX

	if not names:
		return {}
	reasons = {}
	for c in frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Employee Checkin",
			"reference_name": ["in", sorted(names)],
			"comment_type": "Comment",
		},
		fields=["reference_name", "content"],
		order_by="creation desc",
		limit_page_length=0,
	):
		if SKIP_PREFIX in (c.content or "") and c.reference_name not in reasons:
			reasons[c.reference_name] = frappe.utils.strip_html(c.content)
	return reasons


def skipped_tap_verdict(text, rejected: bool, closer: bool) -> tuple[bool, str]:
	"""(fixable, reason) for one skip-stamped tap from its reason comment. Pure."""
	from hrms.utils.attendance_day_audit import REPAIRABLE_SKIP_REASONS

	suffix = " — the only closer of a lone IN" if closer else ""
	if rejected:
		return False, f"rejected by the approver{suffix}: HR keys the OUT or hands the day back"
	if not text:
		return False, f"skipped with no reason comment (hand tick or API){suffix}: HR un-skips or keys it"
	if any(phrase in text for phrase in REPAIRABLE_SKIP_REASONS):
		return True, f"repairable skip ({text[:80]}){suffix}"
	return False, f"{text[:120]}{suffix}"


def _plan_skipped_taps(win, for_update=False, ctx=None) -> dict:
	"""F7/F14: every skip-stamped tap in the window — a repairable reason is fixable
	(skip_stamps); no reason, by hand, or rejected-but-only-closer goes to HR."""
	ctx = ctx or _context(win)
	skipped = [t for t in ctx["taps"] if cint(t.get("skip_auto_attendance"))]
	reasons = _skip_reasons([t.name for t in skipped])
	planned, held = [], []
	for tap in skipped:
		day = ctx["anchors"].get(tap.name) or getdate(tap.time)
		if not _in_window(win, day):
			continue
		day_taps = ctx["days"].get((tap.employee, day), [])
		closer = only_closer(day_taps if tap in day_taps else [*day_taps, tap], tap)
		rejected = tap.get("remote_approval_status") == "Rejected"
		if rejected and not closer:
			continue  # a rejection that left the day whole is a decision, not damage
		row = _live_row(ctx, tap.employee, day)
		entry = _unclaimable(
			"F7",
			tap.employee,
			day,
			None,
			employee_name=tap.employee_name,
			shift=tap.shift,
			attendance=row and row.name,
			status=row and row.status,
			taps=len(day_taps),
			checkin=tap.name,
			time=str(tap.time),
			log_type=tap.log_type,
			only_closer=closer,
			skip_reason=reasons.get(tap.name),
		)
		protection = _protection(ctx, tap.employee, day, for_update)
		if protection:
			held.append(_held(entry, protection))
			continue
		fixable, reason = skipped_tap_verdict(reasons.get(tap.name), rejected, closer)
		(planned.append({**entry, "reason": reason}) if fixable else held.append(_held(entry, reason)))
	logger.info(
		"[attendance_recovery] F7 %s..%s: %d repairable, %d held", win.start, win.end, len(planned), len(held)
	)
	return _outcome(planned, held)


def late_checkout_broken(row, punch) -> str | None:
	"""Why the day still reads wrong after a late check-out, or None. Pure."""
	if row is None:
		return "no submitted attendance row"
	if row.get("status") == "Half Day":
		return f"{row.get('name')} is still Half Day"
	if not row.get("out_time"):
		return f"{row.get('name')} has no out time"
	if cint(punch.get("skip_auto_attendance")):
		return "the check-out punch is skip-stamped"
	if not punch.get("attendance"):
		return "the check-out punch is not linked to the row"
	return None


def _plan_late_checkout_requests(win, for_update=False, ctx=None) -> dict:
	"""F9: approved (fixable: reprocess) or stale pending (HR) late check-outs whose day
	still reads Half Day / no out time / OUT unlinked or skipped, plus orphan late OUTs
	whose request was deleted."""
	ctx = ctx or _context(win)
	requests = frappe.get_all(
		"Remote Checkin Request",
		filters={
			"status": ["in", ["Approved", "Pending"]],
			"is_late_checkout": 1,
			"checkin_time": [
				"between",
				[
					datetime.combine(win.start, time.min),
					datetime.combine(win.end + timedelta(days=2), time.min),
				],
			],
		},
		fields=["name", "employee", "employee_name", "checkin", "checkin_time", "status", "creation"],
		limit_page_length=0,
	)
	taps = {t.name: t for t in ctx["taps"]}
	today, planned, held = _today(), [], []
	for request in requests:
		punch = taps.get(request.checkin)
		day = (ctx["anchors"].get(request.checkin) if punch else None) or getdate(
			punch.time if punch else request.checkin_time
		)
		if not _in_window(win, day):
			continue
		row = _live_row(ctx, request.employee, day)
		entry = _unclaimable(
			"F9",
			request.employee,
			day,
			None,
			employee_name=request.employee_name,
			shift=punch and punch.shift,
			attendance=row and row.name,
			status=row and row.status,
			taps=len(ctx["days"].get((request.employee, day), [])),
			request=request.name,
			request_status=request.status,
			checkin=request.checkin,
		)
		if not punch:
			held.append(_held(entry, f"the late check-out punch of {request.name} was deleted"))
			continue
		why = late_checkout_broken(row, punch)
		if not why:
			continue
		if request.status == "Pending":
			age = (today - getdate(request.creation)).days
			if age >= LATE_CHECKOUT_STALE_DAYS:
				held.append(
					_held(entry, f"late check-out pending for {age} days ({why}): approver never acted")
				)
			continue
		protection = _protection(ctx, request.employee, day, for_update)
		if protection:
			held.append(_held(entry, protection))
		else:
			planned.append({**entry, "reason": f"approved late check-out, {why}"})
	# Orphans: an OUT that asked for approval but no request refers to it any more.
	asked = [
		t
		for t in ctx["taps"]
		if t.log_type == "OUT"
		and t.get("remote_approval_status") in ("Pending", "Approved")
		and _in_window(win, ctx["anchors"].get(t.name) or getdate(t.time))
	]
	referenced = (
		set(
			frappe.get_all(
				"Remote Checkin Request",
				filters={"checkin": ["in", sorted(t.name for t in asked)]},
				pluck="checkin",
				limit_page_length=0,
			)
		)
		if asked
		else set()
	)
	for tap in asked:
		if tap.name in referenced:
			continue
		day = ctx["anchors"].get(tap.name) or getdate(tap.time)
		row = _live_row(ctx, tap.employee, day)
		why = late_checkout_broken(row, tap)
		if not why:
			continue
		entry = _unclaimable(
			"F9",
			tap.employee,
			day,
			None,
			employee_name=tap.employee_name,
			shift=tap.shift,
			attendance=row and row.name,
			status=row and row.status,
			taps=len(ctx["days"].get((tap.employee, day), [])),
			checkin=tap.name,
			request=None,
		)
		reason = _protection(ctx, tap.employee, day, for_update)
		held.append(_held(entry, reason or f"orphan OUT: its approval request was deleted ({why})"))
	logger.info(
		"[attendance_recovery] F9 %s..%s: %d to reprocess, %d held",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def _plan_present_without_live_taps(win, for_update=False, ctx=None) -> dict:
	"""F13: a submitted, engine-marked Present / Half Day row whose linked taps are all
	rejected, or none at all (the row outlived its evidence)."""
	ctx = ctx or _context(win)
	linked = {}
	for tap in ctx["taps"]:
		if tap.get("attendance"):
			linked.setdefault(tap.attendance, []).append(tap)
	planned, held = [], []
	for row in sorted(ctx["rows"], key=lambda r: (str(r.employee), str(r.attendance_date))):
		if (
			cint(row.get("docstatus")) != 1
			or row.get("status") not in ("Present", "Half Day")
			or not cint(row.get("auto_attendance"))
			or row.get(PROVENANCE_FIELD)
		):
			continue
		taps = linked.get(row.name, [])
		if any(t.get("remote_approval_status") != "Rejected" for t in taps):
			continue
		day = getdate(row.attendance_date)
		why = f"all {len(taps)} linked tap(s) rejected" if taps else "no tap linked"
		entry = _unclaimable(
			"F13",
			row.employee,
			day,
			f"{row.status} row with {why}",
			employee_name=row.employee_name,
			shift=row.shift,
			attendance=row.name,
			status=row.status,
			taps=len(ctx["days"].get((row.employee, day), [])),
		)
		reason = _protection(ctx, row.employee, day, for_update)
		(held.append(_held(entry, reason)) if reason else planned.append(entry))
	logger.info(
		"[attendance_recovery] F13 %s..%s: %d to rebuild, %d held",
		win.start,
		win.end,
		len(planned),
		len(held),
	)
	return _outcome(planned, held)


def unclaimable_rows(win, families=None, ctx=None) -> list:
	"""One row per detected employee-day (or tap / assignment pair) with family, reason,
	status (fixable / on purpose / needs HR) — the "Unclaimable Days" report's rows."""
	ctx = ctx or _context(win)
	wanted = set(families or [f for f, *_rest in UNCLAIMABLE_FAMILIES])
	rows = []
	for family, _name, fix, planner in UNCLAIMABLE_FAMILIES:
		if family not in wanted:
			continue
		plan = globals()[planner](win, ctx=ctx)
		rows.extend({**p, "family": family, "status": STATUS_FIXABLE, "fix": fix} for p in plan["planned"])
		rows.extend(
			{**h, "family": family, "status": row_status(h, True), "fix": fix} for h in plan["held_back"]
		)
	rows.sort(key=lambda r: (str(r.get("employee")), str(r.get("date")), r.get("family")))
	logger.info("[attendance_recovery] unclaimable %s..%s: %s", win.start, win.end, family_counts(rows))
	return rows


def _shift_length_minutes(start_time, end_time) -> int:
	return (_minutes(end_time) - _minutes(start_time)) % (24 * 60) or 24 * 60


def shift_issues(shift, assigned: int) -> list:
	"""Config problems of one Shift Type row, as text. Pure."""
	length = _shift_length_minutes(shift.get("start_time"), shift.get("end_time"))
	before = cint(shift.get("begin_check_in_before_shift_start_time"))
	after = cint(shift.get("allow_check_out_after_shift_end_time"))
	found = []
	if before > length or after > length:
		found.append(f"a check-in buffer ({before}/{after} min) is longer than the shift ({length} min)")
	elif max(before, after) > BUFFER_WARN_MINUTES:
		found.append(
			f"buffers {before}/{after} min exceed {BUFFER_WARN_MINUTES}: neighbouring shift windows overlap"
		)
	if (
		shift.get("determine_check_in_and_check_out") == ALTERNATING
		and shift.get("working_hours_calculation_based_on") == FIRST_LAST
	):
		found.append(
			"hours are first-in/last-out while pairing alternates: a mid-day gap is paid as hours, not OT"
		)
	if assigned and not cint(shift.get("enable_auto_attendance")):
		found.append(f"auto attendance is off while {assigned} employee(s) are assigned")
	elif assigned and (not shift.get("process_attendance_after") or not shift.get("last_sync_of_checkin")):
		found.append("auto attendance is on but Process Attendance After / Last Sync of Checkin is empty")
	return found


def config_health() -> dict:
	"""F15/F16: per Shift Type hours, buffers, mode mix, auto attendance, holiday list;
	per employee overlapping Active assignments. REPORT ONLY — shift config is HR's."""
	shifts = frappe.get_all(
		"Shift Type",
		fields=[
			"name",
			"start_time",
			"end_time",
			"begin_check_in_before_shift_start_time",
			"allow_check_out_after_shift_end_time",
			"determine_check_in_and_check_out",
			"working_hours_calculation_based_on",
			"enable_auto_attendance",
			"process_attendance_after",
			"last_sync_of_checkin",
			"holiday_list",
		],
		limit_page_length=0,
	)
	today = _today()
	assignments = _submitted_assignments(today, today)
	assigned = {}
	for a in assignments:
		assigned.setdefault(a.shift_type, set()).add(a.employee)
	issues, table = [], []
	for s in shifts:
		staff = assigned.get(s.name, set())
		table.append(
			{
				"shift": s.name,
				"start": str(s.start_time),
				"end": str(s.end_time),
				"hours": round(_shift_length_minutes(s.start_time, s.end_time) / 60, 2),
				"buffer_before": cint(s.begin_check_in_before_shift_start_time),
				"buffer_after": cint(s.allow_check_out_after_shift_end_time),
				"pairing": s.determine_check_in_and_check_out,
				"hours_mode": s.working_hours_calculation_based_on,
				"auto_attendance": cint(s.enable_auto_attendance),
				"holiday_list": s.holiday_list,
				"assigned": len(staff),
			}
		)
		issues.extend(
			{"scope": "shift", "name": s.name, "issue": text} for text in shift_issues(s, len(staff))
		)
	times = {s.name: (s.start_time, s.end_time) for s in shifts}
	by_employee = {}
	for a in assignments:
		by_employee.setdefault(a.employee, []).append(a)
	for employee, own in sorted(by_employee.items()):
		for i, a in enumerate(own):
			for b in own[i + 1 :]:
				if a.shift_type == b.shift_type or a.shift_type not in times or b.shift_type not in times:
					continue
				if shifts_overlap(times[a.shift_type], times[b.shift_type]):
					issues.append(
						{
							"scope": "employee",
							"name": employee,
							"issue": f"Active assignments {a.name} ({a.shift_type}) and {b.name} ({b.shift_type}) "
							"overlap by scheduled hours",
						}
					)
	uncovered = _employees_without_holiday_list(
		{e for s in shifts if not s.holiday_list for e in assigned.get(s.name, set())}, today
	)
	issues.extend(
		{
			"scope": "employee",
			"name": employee,
			"issue": "no holiday list on the shift, the employee or the company: rest days price as workdays",
		}
		for employee in sorted(uncovered)
	)
	logger.info("[attendance_recovery] config health: %d shift(s), %d issue(s)", len(shifts), len(issues))
	return {"shifts": table, "issues": issues, "count": len(issues)}


def _employees_without_holiday_list(employees, as_on) -> set:
	from hrms.utils.holiday_list import get_holiday_list_for_employee

	missing = set()
	for employee in employees:
		try:
			if not get_holiday_list_for_employee(employee, raise_exception=False, as_on=as_on):
				missing.add(employee)
		except Exception:
			logger.exception("[attendance_recovery] holiday list of %s unreadable", employee)
	return missing


def _config_section() -> dict:
	health = config_health()
	return {
		"fix": None,
		"family": "F16",
		"note": "report only: shift config is HR's and is never edited here",
		"count": health["count"],
		"count_fixable": 0,
		"count_needs_hr": health["count"],
		"count_on_purpose": 0,
		"sample": health["issues"][:SAMPLE],
		"shifts": health["shifts"],
	}
