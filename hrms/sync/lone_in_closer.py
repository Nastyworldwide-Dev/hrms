"""Close a pre-cutover lone IN with the clock-OUT the old ERP still holds. Add-only.

Before cutover (4 September 2026) staff punched on the source ERP as well as
here, and the mirror stopped carrying Employee Checkin at cutover. A day that
holds exactly one tap here (the IN) while its OUT sits only on the ERP marks
as Half Day / 0 h for ever: no automatic step ever brought that OUT across
(attendance-lost-ot-plan, family F3, edge E10). Owner decision D3 (15 Sep 2026):
copy it, narrowly.

The rule is IN-anchored (`choose_closing_punch`): the closing tap is the ERP's
NEXT punch after the hub IN within `CLOSE_WITHIN`, whatever the ERP labelled
it — the ERP's own log types are not trusted (an OUT typed IN is the usual
shape). Nothing is copied when:

* the ERP holds no punch in that span ("no clock-out on ERP within 20 h" —
  the day stays on HR's list, ruling: a lone IN is never invented closed);
* a hub tap already sits within ±`DUPLICATE_TOLERANCE` of the candidate — the
  tap is here, skipped or rejected, and a person decides;
* the candidate falls at or after the employee's next hub tap;
* the employee-day is protected: removed by HR in Shift Attendance, marked by
  HR by hand, a leave / half-day-leave / Attendance Request row, a draft HR is
  keying, or a payout depends on it (`_repair_financial_dependency`).

The write is `checkin_import.insert_source_punch`: an OUT under this hub's own
autoname, `source_checkin` = "<instance>::<ERP name>" (the unique index makes
a second copy impossible), `device_id` "ERP-CLOSER", phone-punch validation
skipped exactly as every imported punch, the shift stamp inherited from the
IN it closes by the override. Nothing is ever updated or deleted; the caller
(attendance recovery) rebuilds the day afterwards.

Off switch: HR Settings `attendance_close_lone_ins_from_erp` (absent = on).
Refused while a sync run is in flight for the instance, and when no single
enabled instance carries credentials or the ERP refuses them (fail closed).
"""

import logging
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import cint, get_datetime, getdate

from hrms.sync.missing_checkins import DOCTYPE, REMOTE_FIELDS, _to_second, local_employees

logger = logging.getLogger(__name__)

#: unlock_mirrored_writes day; the last day this closer may touch is the one before.
CUTOVER = date(2026, 9, 4)
LAST_DAY = CUTOVER - timedelta(days=1)
#: The session rule: a tap up to this long after the IN closes it.
CLOSE_WITHIN = timedelta(hours=20)
#: A hub tap this close to the ERP candidate is the same tap, not a missing one.
DUPLICATE_TOLERANCE = timedelta(minutes=3)
DEVICE_ID = "ERP-CLOSER"
SETTING = "attendance_close_lone_ins_from_erp"
ROW_SAVEPOINT = "hrms_lone_in_closer_row"
COMMIT_EVERY = 50
ATTENDANCE_FIELDS = [
	"name",
	"docstatus",
	"status",
	"out_time",
	"auto_attendance",
	"leave_type",
	"leave_application",
	"attendance_request",
	"modify_half_day_status",
]
NO_CLOSER = "no clock-out on ERP within 20 h"
DUPLICATE = "already recorded in Verifica — duplicate"
AFTER_NEXT_IN = "the ERP punch falls after the next Verifica tap"


# --- pure -----------------------------------------------------------------------


def _fmt(moment: datetime) -> str:
	return moment.strftime("%Y-%m-%d %H:%M:%S")


def choose_closing_punch(in_time: datetime, remote_rows) -> dict | None:
	"""The ERP punch that closes this IN, or None. Pure.

	The first ERP punch strictly after the IN, not at the IN's own second (that
	is the ERP's copy of the same tap), within `CLOSE_WITHIN`. Its log_type is
	recorded, never consulted.
	"""
	in_second = _to_second(in_time)
	latest = in_second + CLOSE_WITHIN
	rows = sorted(
		({**row, "time": _to_second(row.get("time"))} for row in remote_rows),
		key=lambda row: (row["time"], row.get("name") or ""),
	)
	for row in rows:
		if in_second < row["time"] <= latest:
			return row
	return None


def near_duplicate(candidate_time: datetime, hub_taps) -> bool:
	"""A hub tap of any state (skipped, rejected, mirrored) within ±3 min. Pure."""
	moment = _to_second(candidate_time)
	return any(abs(_to_second(tap.get("time")) - moment) <= DUPLICATE_TOLERANCE for tap in hub_taps)


def protection_reason(rows, financial=None, removed_by_hr=False) -> str | None:
	"""Why this employee-day must not be closed, or None. Pure.

	`rows` are the day's Attendance rows (docstatus < 2); `financial` is what
	`_repair_financial_dependency` returned for the day.
	"""
	if removed_by_hr:
		return "removed by HR in Shift Attendance: HR hands it back first"
	for row in rows:
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


def _counted(tap) -> bool:
	return tap.get("remote_approval_status") != "Rejected" and not cint(tap.get("skip_auto_attendance"))


def lone_in_days(taps, start: date, end: date) -> list[dict]:
	"""[{employee, date, in_tap, next_tap}] for every employee-day in [start, end]
	whose only counted tap is typed IN. Pure. `taps` are one employee's hub taps,
	any state, any provenance; `next_tap` is the first tap of any state after
	the IN, or None.
	"""
	ordered = sorted(taps, key=lambda tap: get_datetime(tap.get("time")))
	by_day: dict[date, list] = {}
	for tap in ordered:
		if not _counted(tap):
			continue
		by_day.setdefault(getdate(tap.get("shift_start") or tap.get("time")), []).append(tap)
	found = []
	for day, day_taps in sorted(by_day.items()):
		if not (start <= day <= end) or len(day_taps) != 1 or day_taps[0].get("log_type") != "IN":
			continue
		in_tap = day_taps[0]
		in_time = get_datetime(in_tap.get("time"))
		later = (tap for tap in ordered if get_datetime(tap.get("time")) > in_time)
		found.append(
			{"employee": in_tap.get("employee"), "date": day, "in_tap": in_tap, "next_tap": next(later, None)}
		)
	return found


def evaluate(in_time: datetime, remote_rows, hub_taps, next_tap) -> tuple[dict | None, str | None]:
	"""(candidate, None) or (None, hold reason) for one lone-IN day. Pure."""
	candidate = choose_closing_punch(in_time, remote_rows)
	if not candidate:
		return None, NO_CLOSER
	if near_duplicate(candidate["time"], hub_taps):
		return None, DUPLICATE
	if next_tap and candidate["time"] >= _to_second(next_tap.get("time")):
		return None, AFTER_NEXT_IN
	return candidate, None


# --- reads ----------------------------------------------------------------------


def _enabled() -> bool:
	value = frappe.get_single("HR Settings").get(SETTING, 1)
	return cint(1 if value is None else value) == 1


def _source_instance() -> str | None:
	"""The one enabled ERP instance that carries credentials, or None."""
	rows = frappe.get_all(
		"HRMS ERP Instance", filters={"enabled": 1}, fields=["name", "url", "api_key"], limit_page_length=0
	)
	usable = [r.get("name") for r in rows if r.get("url") and r.get("api_key")]
	logger.debug("[lone_in_closer] usable ERP instances: %s", usable)
	return usable[0] if len(usable) == 1 else None


def _sync_running(instance: str) -> bool:
	from hrms.sync.runner import running_run

	return bool(running_run(instance))


def _client(instance: str):
	from hrms.sync.client import RemoteInstanceClient

	return RemoteInstanceClient(instance)


def _hub_taps(employees, start: date, end: date) -> dict:
	"""{employee: [taps]} — every hub tap, any state or provenance, a day before
	the window to two days past it, so a next-day closer and a double tap are seen."""
	if not employees:
		return {}
	rows = frappe.get_all(
		DOCTYPE,
		filters=[
			["employee", "in", sorted(employees)],
			["time", ">=", datetime.combine(start - timedelta(days=1), datetime.min.time())],
			["time", "<", datetime.combine(end + timedelta(days=2), datetime.min.time())],
		],
		fields=[
			"name",
			"employee",
			"time",
			"log_type",
			"shift",
			"shift_start",
			"skip_auto_attendance",
			"remote_approval_status",
		],
		order_by="time asc",
		limit_page_length=0,
	)
	taps: dict[str, list] = {}
	for row in rows:
		taps.setdefault(row.get("employee"), []).append(row)
	logger.info("[lone_in_closer] %d hub tap(s) for %d employee(s) %s..%s", len(rows), len(taps), start, end)
	return taps


def _attendance_rows(employee: str, day: date) -> list:
	return frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": day, "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
	)


def _financial(employee: str, day: date, rows, for_update: bool):
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	submitted = next((r.get("name") for r in rows if cint(r.get("docstatus")) == 1), None)
	return _repair_financial_dependency(employee, day, submitted, for_update=for_update)


def _removed_by_hr(employee: str, day: date) -> bool:
	from hrms.utils import hr_removed_day

	return hr_removed_day.removed_by_hr(employee, day)


def _erp_punches(client, employee: str, start: datetime, end: datetime) -> list:
	"""The employee's ERP punches with time in [start, end]. One GET per lone day."""
	return client.get_list(
		DOCTYPE,
		filters={"employee": employee, "time": ["between", [_fmt(start), _fmt(end)]]},
		fields=REMOTE_FIELDS,
		limit=None,
		order_by="time asc",
	)


def _held(employee: str, day: date, reason: str) -> dict:
	return {"employee": employee, "date": str(day), "reason": reason, "hr": True}


def _outcome(planned=None, held=None, instance=None, note=None) -> dict:
	held = held or []
	return {
		"planned": planned or [],
		"held_back": held,
		"hr_list": [h for h in held if h.get("hr")],
		"instance": instance,
		"note": note,
	}


# --- the plan ------------------------------------------------------------------------


def plan_close_lone_ins(win, for_update=False) -> dict:
	"""Every pre-cutover lone-IN day in the window with the ERP punch that would
	close it, or why it is held. Reads the ERP; writes nothing. Never raises for
	a missing or refused credential — that is a note.
	"""
	end = min(getdate(win.end), LAST_DAY)
	start = getdate(win.start)
	if start > end:
		return _outcome(note=f"no day before the cutover ({CUTOVER}) in this window")
	if not _enabled():
		return _outcome(note=f"switched off in HR Settings ({SETTING})")
	instance = _source_instance()
	if not instance:
		return _outcome(note="no single enabled ERP instance with credentials: nothing to close")
	if _sync_running(instance):
		return _outcome(instance=instance, note="sync running, skipped")
	try:
		client = _client(instance)
	except Exception as exc:  # fail closed: a credential problem is a note, not a crash
		logger.warning("[lone_in_closer] cannot open %s: %s", instance, exc)
		return _outcome(instance=instance, note=f"cannot read {instance}: {exc}")

	employees = local_employees(instance)
	taps = _hub_taps(set(employees), start, end)
	planned, held = [], []
	for employee, employee_taps in sorted(taps.items()):
		for lone in lone_in_days(employee_taps, start, end):
			day = lone["date"]
			rows = _attendance_rows(employee, day)
			if any(r.get("out_time") for r in rows):
				continue  # not lone: an out time is on the row already
			reason = protection_reason(
				rows, _financial(employee, day, rows, for_update), _removed_by_hr(employee, day)
			)
			if reason:
				held.append(_held(employee, day, reason))
				continue
			in_time = get_datetime(lone["in_tap"].get("time"))
			try:
				remote = _erp_punches(client, employee, in_time, in_time + CLOSE_WITHIN)
			except Exception as exc:
				logger.warning("[lone_in_closer] cannot read %s for %s: %s", instance, employee, exc)
				return _outcome(instance=instance, note=f"cannot read {instance}: {exc}")
			candidate, reason = evaluate(in_time, remote, employee_taps, lone["next_tap"])
			if reason:
				held.append(_held(employee, day, reason))
				continue
			planned.append(
				{
					"employee": employee,
					"date": str(day),
					"in_time": _fmt(_to_second(in_time)),
					"candidate_time": _fmt(candidate["time"]),
					"candidate_source_name": candidate.get("name"),
					"source_log_type": candidate.get("log_type"),
				}
			)
	logger.info(
		"[lone_in_closer] %s %s..%s: %d to close, %d held", instance, start, end, len(planned), len(held)
	)
	return _outcome(planned, held, instance=instance)


# --- the write -------------------------------------------------------------------------


def _insert(entry: dict, instance: str) -> str | None:
	from hrms.sync.checkin_import import insert_source_punch

	return insert_source_punch(
		{
			"employee": entry["employee"],
			"time": entry["candidate_time"],
			"log_type": "OUT",
			"device_id": DEVICE_ID,
			"remote_name": entry["candidate_source_name"],
		},
		instance,
	)


def _lock(instance: str) -> bool:
	from hrms.sync.checkin_import import _lock_instance

	return _lock_instance(instance)


def apply_close_lone_ins(win, plan) -> dict:
	"""Insert the planned OUTs, one savepoint per row, a commit per 50. Insert-only:
	a row already here (same second, or the same ERP punch via the unique index)
	is skipped, never updated."""
	from hrms.sync.checkin_import import is_source_key_duplicate
	from hrms.utils.offshift_punch_heal import _lost_transaction

	instance = plan.get("instance")
	planned = plan.get("planned") or []
	if not planned:
		return {"done": [], "held_back": []}
	if not _enabled():
		return {
			"done": [],
			"held_back": [{**e, "reason": f"switched off ({SETTING})", "hr": False} for e in planned],
		}
	if _sync_running(instance) or not _lock(instance):
		return {
			"done": [],
			"held_back": [{**e, "reason": "sync running, skipped", "hr": False} for e in planned],
		}
	done, held = [], []
	for index, entry in enumerate(planned, start=1):
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			name = _insert(entry, instance)
		except Exception as exc:
			if _lost_transaction(exc):
				raise
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			if is_source_key_duplicate(exc):
				from frappe.utils.messages import clear_last_message

				clear_last_message()
				done.append({**entry, "checkin": None, "already": True})
				continue
			logger.exception("[lone_in_closer] %s on %s not closed", entry["employee"], entry["date"])
			held.append({**entry, "reason": f"could not be inserted: {exc}", "hr": True})
			continue
		done.append({**entry, "checkin": name, "already": name is None})
		if index % COMMIT_EVERY == 0:
			frappe.db.commit()
	frappe.db.commit()
	logger.info("[lone_in_closer] %s: %d closed, %d held", instance, len(done), len(held))
	return {"done": done, "held_back": held}
