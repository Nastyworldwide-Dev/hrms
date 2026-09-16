"""The old ERP's pre-cutover punches: compare them with this hub, then copy them.

Before cutover (4 September 2026) staff punched on the source ERP as well as
here, and the mirror never carried Employee Checkin for those days. What the
hub holds for 1 August → 3 September is therefore a PARTIAL punch set: days
read Half Day, Absent or 0 h although the ERP holds the tap that closes them
(attendance-endgame-plan B1/B2, live: 13/17/21/27 August have no OUT here at
all, and the narrow lone-IN closer only ever looked at days with exactly one
tap).

This module has two halves, and the reporting half comes first:

* `parity` (read-only, always allowed) — per employee-day: the ERP's punches,
  this hub's punches, what the hub day currently reads, and a verdict. It only
  ever GETs from the ERP (`RemoteInstanceClient` can issue nothing else) and
  writes nothing here;
* the copy (`backfill_punches`) — insert-only, source-keyed, behind an HR
  Settings switch that reads as OFF while its field does not exist.

A punch within `DUPLICATE_TOLERANCE` of one on the other side is the SAME
punch: the two clocks and the two apps do not agree to the second, and the
copy refuses a tap that close to an existing one. The report uses the same
tolerance, so what it says is missing is exactly what a copy would insert.
"""

import logging
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms.sync.checkin_import import attendance_day, is_source_key_duplicate
from hrms.sync.missing_checkins import DOCTYPE, REMOTE_FIELDS, _to_second
from hrms.utils.dry_run import wants_dry_run

logger = logging.getLogger(__name__)

#: unlock_mirrored_writes day: the last day this module may touch is the one before.
CUTOVER = date(2026, 9, 4)
LAST_DAY = CUTOVER - timedelta(days=1)
#: Recovery's floor — OT stays claimable four cycles back.
FLOOR = date(2026, 8, 1)
#: Two taps this close are the same tap, on either side.
DUPLICATE_TOLERANCE = timedelta(minutes=3)
#: HR Settings Check; ABSENT OR UNTICKED = off. Only the copy asks it.
SWITCH = "attendance_erp_backfill"
#: HR Settings Small Text, comma-separated Employee ids; empty = everyone.
PILOT = "attendance_rebuild_pilot_employees"
MAX_WINDOW_DAYS = 62
#: One punch's insert rolls back alone.
ROW_SAVEPOINT = "hrms_erp_backfill_row"
#: Commit this often, then take the instance lock again (the lone_in_closer lesson).
COMMIT_EVERY = 50
DEVICE_ID = "ERP-BACKFILL"
DUPLICATE = "already recorded in Verifica — duplicate"


# --- pure -----------------------------------------------------------------------


def _fmt(moment: datetime) -> str:
	return _to_second(moment).strftime("%Y-%m-%d %H:%M:%S")


def match_punches(erp_times, hub_times, tolerance=DUPLICATE_TOLERANCE) -> dict:
	"""Match each ERP punch to at most one hub tap within `tolerance`. Pure.

	Returns {matched: [(erp, hub)], missing: [erp with no hub tap], extra: [hub
	taps no ERP punch claims]}. One-to-one and nearest-first, so two ERP punches
	a minute apart need two hub taps, not one standing for both.
	"""
	erp = sorted(_to_second(moment) for moment in erp_times)
	remaining = sorted(_to_second(moment) for moment in hub_times)
	matched, missing = [], []
	for moment in erp:
		near = min(remaining, key=lambda hub: abs(hub - moment), default=None)
		if near is not None and abs(near - moment) <= tolerance:
			remaining.remove(near)
			matched.append((moment, near))
		else:
			missing.append(moment)
	logger.debug(
		"[erp_backfill] matched %d, missing %d, extra %d", len(matched), len(missing), len(remaining)
	)
	return {"matched": matched, "missing": missing, "extra": remaining}


def day_verdict(match: dict, row) -> str:
	"""What one employee-day's comparison says, in HR's words. Pure."""
	parts = []
	if match["missing"]:
		parts.append(f"hub missing {len(match['missing'])}")
	if match["extra"]:
		parts.append(f"hub extra {len(match['extra'])}")
	if not row:
		parts.append("no hub row")
	return ", ".join(parts) if parts else "matches"


def _punch_day(row) -> date:
	"""The shift day a punch belongs to: the hub's own stamp, or the past-midnight rule."""
	stamped = row.get("shift_start")
	if stamped:
		return getdate(stamped)
	return attendance_day({"time": _to_second(row.get("time")), "log_type": row.get("log_type")})


def parity_rows(employee, erp_rows, hub_rows, attendance, start: date, end: date) -> list:
	"""One line per employee-day in [start, end]: both sides' punches and a verdict. Pure.

	`attendance` maps (employee, day) to that day's live Attendance row, or is
	missing the key when the hub has no row for the day.
	"""
	sides: dict = {}
	for row in erp_rows:
		sides.setdefault(_punch_day(row), {"erp": [], "hub": []})["erp"].append(_to_second(row.get("time")))
	for row in hub_rows:
		sides.setdefault(_punch_day(row), {"erp": [], "hub": []})["hub"].append(_to_second(row.get("time")))
	lines = []
	for day in sorted(sides):
		if not (start <= day <= end):
			continue
		match = match_punches(sides[day]["erp"], sides[day]["hub"])
		row = attendance.get((employee, day)) or {}
		lines.append(
			{
				"employee": employee,
				"date": str(day),
				"erp_punches": len(sides[day]["erp"]),
				"hub_punches": len(sides[day]["hub"]),
				"erp_times": [_fmt(moment) for moment in sorted(sides[day]["erp"])],
				"hub_times": [_fmt(moment) for moment in sorted(sides[day]["hub"])],
				"missing_on_hub": [_fmt(moment) for moment in match["missing"]],
				"extra_on_hub": [_fmt(moment) for moment in match["extra"]],
				"attendance": row.get("name"),
				"status": row.get("status"),
				"working_hours": flt(row.get("working_hours")) if row else None,
				"verdict": day_verdict(match, row.get("name")),
			}
		)
	logger.info("[erp_backfill] %s: %d employee-day line(s) in %s..%s", employee, len(lines), start, end)
	return lines


def pilot_employees(text, employees=None) -> list | None:
	"""The pilot list from HR Settings, narrowed by `employees`. Pure.

	Empty or missing text means everyone (None). A pilot list is a FENCE: an
	employee outside it is dropped even when the caller asked for them by name.
	"""
	pilot = [part.strip() for part in str(text or "").replace("\n", ",").split(",") if part.strip()]
	if not pilot:
		return list(employees) if employees else None
	if employees:
		pilot = [name for name in pilot if name in set(employees)]
	logger.info("[erp_backfill] pilot list holds %d employee(s)", len(pilot))
	return pilot


def resolve_window(from_date, to_date) -> tuple:
	"""[start, end] for a pre-cutover pass. Refuses today, the cutover and after."""
	start, end = getdate(from_date), getdate(to_date)
	if start < FLOOR:
		logger.info("[erp_backfill] %s is before the floor; reading from %s", start, FLOOR)
		start = FLOOR
	if end > LAST_DAY:
		raise ValueError(
			f"{end} is on or after the cutover ({CUTOVER}); this hub owns those days. "
			f"Ask for {LAST_DAY} or earlier."
		)
	if start > end:
		raise ValueError(f"from_date {start} is after to_date {end}")
	if (end - start).days + 1 > MAX_WINDOW_DAYS:
		raise ValueError(f"{(end - start).days + 1} days; run at most {MAX_WINDOW_DAYS} days per call")
	return start, end


# --- reads ----------------------------------------------------------------------


def _enabled() -> bool:
	"""HR Settings `attendance_erp_backfill`. A field that is absent reads as OFF."""
	try:
		return cint(frappe.get_single("HR Settings").get(SWITCH)) == 1
	except Exception:
		logger.exception("[erp_backfill] could not read the %s switch; treating it as off", SWITCH)
		return False


def _pilot_text() -> str:
	try:
		return frappe.get_single("HR Settings").get(PILOT) or ""
	except Exception:
		logger.exception("[erp_backfill] could not read %s; treating it as empty", PILOT)
		return ""


def _source_instance() -> str | None:
	"""The one enabled ERP instance that carries credentials, or None."""
	from hrms.sync.lone_in_closer import _source_instance as resolve

	return resolve()


def _client(instance: str):
	from hrms.sync.client import RemoteInstanceClient

	return RemoteInstanceClient(instance)


def _employees_in_scope(instance: str, employees=None) -> list:
	"""Hub Employees stamped from this instance, narrowed by `employees`."""
	from hrms.sync.missing_checkins import local_employees

	known = local_employees(instance)
	scope = [name for name in sorted(known) if not employees or name in set(employees)]
	logger.info("[erp_backfill] %s: %d employee(s) in scope", instance, len(scope))
	return scope


def _erp_punches(client, employee: str, start: date, end: date) -> list:
	"""One paged GET per employee: their ERP punches over the window, a day past
	each edge so a past-midnight OUT and an early IN are both seen."""
	first = datetime.combine(start, datetime.min.time())
	last = datetime.combine(end + timedelta(days=2), datetime.min.time())
	rows = client.get_list(
		DOCTYPE,
		filters={"employee": employee, "time": ["between", [_fmt(first), _fmt(last)]]},
		fields=REMOTE_FIELDS,
		limit=None,
		order_by="time asc",
	)
	logger.info("[erp_backfill] %s: %d ERP punch(es) %s..%s", employee, len(rows), start, end)
	return rows


def _hub_punches(employees, start: date, end: date) -> dict:
	"""{employee: [taps]} — every hub tap of any state or provenance on those shift days."""
	if not employees:
		return {}
	first = datetime.combine(start - timedelta(days=1), datetime.min.time())
	last = datetime.combine(end + timedelta(days=2), datetime.min.time())
	rows = frappe.get_all(
		DOCTYPE,
		filters=[
			["employee", "in", sorted(employees)],
			["time", ">=", first],
			["time", "<", last],
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
	taps: dict = {}
	for row in rows:
		taps.setdefault(row.get("employee"), []).append(row)
	logger.info("[erp_backfill] %d hub tap(s) for %d employee(s) %s..%s", len(rows), len(taps), start, end)
	return taps


def _attendance_rows(employees, start: date, end: date) -> dict:
	"""{(employee, day): row} for every live Attendance in the window."""
	if not employees:
		return {}
	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", sorted(employees)],
			"attendance_date": ["between", [start, end]],
			"docstatus": ["<", 2],
		},
		fields=["name", "employee", "attendance_date", "status", "docstatus", "working_hours", "out_time"],
		limit_page_length=0,
	)
	found = {(row.get("employee"), getdate(row.get("attendance_date"))): row for row in rows}
	logger.info("[erp_backfill] %d live attendance row(s) %s..%s", len(found), start, end)
	return found


def parity(from_date, to_date, employees=None) -> dict:
	"""Per employee-day: the ERP's punches, this hub's, and what the hub day reads.

	Read-only on both sides, and never gated by the write switch — a report is
	always allowed. Raises ValueError for a window this module may not speak for.
	"""
	start, end = resolve_window(from_date, to_date)
	instance = _source_instance()
	if not instance:
		logger.warning("[erp_backfill] no single enabled ERP instance with credentials")
		return {"instance": None, "rows": [], "counts": {}, "note": "no source ERP to compare with"}
	client = _client(instance)
	scope = _employees_in_scope(instance, employees)
	hub = _hub_punches(scope, start, end)
	attendance = _attendance_rows(scope, start, end)
	lines = []
	for employee in scope:
		lines.extend(
			parity_rows(
				employee,
				_erp_punches(client, employee, start, end),
				hub.get(employee, []),
				attendance,
				start,
				end,
			)
		)
	counts = {
		"employees": len(scope),
		"days": len(lines),
		"days_matching": sum(1 for line in lines if line["verdict"] == "matches"),
		"hub_missing_punches": sum(len(line["missing_on_hub"]) for line in lines),
		"hub_extra_punches": sum(len(line["extra_on_hub"]) for line in lines),
	}
	logger.info("[erp_backfill] parity %s..%s: %s", start, end, counts)
	return {
		"instance": instance,
		"window": {"from_date": str(start), "to_date": str(end)},
		"rows": sorted(lines, key=lambda line: (line["date"], line["employee"])),
		"counts": counts,
	}


@frappe.whitelist()
def parity_report(from_date, to_date, employees=None) -> dict:
	"""Whitelisted read of `parity`, for HR Manager / System Manager only.

	Company-fenced HR is refused: the comparison spans the whole source
	instance, which is every company on it.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("compare punches with the source ERP across the whole hub"))
	if isinstance(employees, str):
		employees = [part.strip() for part in employees.split(",") if part.strip()]
	try:
		result = parity(from_date, to_date, employees)
	except ValueError as exc:
		frappe.throw(str(exc))
	logger.info("[erp_backfill] parity read by %s", frappe.session.user)
	return result


# --- the copy ---------------------------------------------------------------------


def near_duplicate(moment, hub_taps, tolerance=DUPLICATE_TOLERANCE) -> bool:
	"""Is a hub tap of ANY state within `tolerance` of this ERP punch? Pure.

	Skipped and rejected taps count: the tap IS here and a person decided about
	it, so copying it back would undo that decision.
	"""
	moment = _to_second(moment)
	return any(abs(_to_second(tap.get("time")) - moment) <= tolerance for tap in hub_taps)


def plan_backfill(employee, erp_rows, hub_taps, start: date, end: date) -> tuple:
	"""(to insert, refused) for one employee, before any day protection. Pure.

	Only this employee's ERP punches, only shift days inside the window, and
	never a punch a hub tap already stands for.
	"""
	planned, refused = [], []
	for row in sorted(erp_rows, key=lambda r: (_to_second(r.get("time")), r.get("name") or "")):
		if row.get("employee") != employee:
			continue
		day = _punch_day(row)
		if not (start <= day <= end):
			continue
		entry = {
			"employee": employee,
			"date": str(day),
			"time": _fmt(row.get("time")),
			"log_type": row.get("log_type"),
			"remote_name": row.get("name"),
		}
		if near_duplicate(row.get("time"), hub_taps):
			refused.append({**entry, "reason": DUPLICATE, "hr": False})
		else:
			planned.append(entry)
	logger.info("[erp_backfill] %s: %d punch(es) to copy, %d refused", employee, len(planned), len(refused))
	return planned, refused


def _sync_running(instance: str) -> bool:
	from hrms.sync.runner import running_run

	return bool(running_run(instance))


def _lock(instance: str) -> bool:
	from hrms.sync.checkin_import import _lock_instance

	return _lock_instance(instance)


def _lock_employee(employee: str) -> None:
	from hrms.hr.doctype.shift_type.shift_type import lock_employee_row

	lock_employee_row(employee)


def _protection(employee: str, day: date, for_update: bool = True) -> str | None:
	"""Why this employee-day must be left alone, or None.

	Recovery's own rule and nothing beside it: today, HR-removed, a draft, a
	leave or request (live, not just a row), a paid or approved-OT day, and —
	through the ownership classifier it now asks — a day a person owns.
	"""
	from hrms.utils import attendance_recovery as rec

	held = rec._day_protection(employee, getdate(day), for_update)
	if held:
		logger.info("[erp_backfill] %s on %s held: %s", employee, day, held)
	return held


def _insert(entry: dict, instance: str) -> str | None:
	from hrms.sync.checkin_import import insert_source_punch

	logger.debug("[erp_backfill] copying %s for %s", entry["remote_name"], entry["employee"])
	return insert_source_punch(
		{
			"employee": entry["employee"],
			"time": entry["time"],
			"log_type": entry.get("log_type"),
			"device_id": DEVICE_ID,
			"remote_name": entry["remote_name"],
		},
		instance,
	)


def _guarded_rebuild(employee: str, day: date) -> dict:
	"""The engine's own re-mark of the day, under the never-worse guard (B4)."""
	from hrms.utils import attendance_recovery as rec

	return rec.guarded_rebuild(employee, getdate(day), rec._remark_released_day)


def rebuild_days(days, instance: str) -> dict:
	"""Rebuild every copied employee-day through the engine, oldest first.

	The instance lock is taken here in its own right: the insert phase's last
	commit released it, so without this the whole rebuild would race a sync that
	started meanwhile. Per-day savepoint, per-employee lock, small batches,
	resumable — a day already rebuilt marks the same result the second time.
	Never raises: one bad day is held for HR and the rest go on.
	"""
	ordered = sorted(days, key=lambda pair: (pair[1], str(pair[0])))
	if not _lock(instance):
		logger.warning("[erp_backfill] %s: sync running, no day rebuilt", instance)
		return {
			"rebuilt": [],
			"held_back": [
				{"employee": e, "date": str(d), "reason": "sync running, skipped", "hr": False}
				for e, d in ordered
			],
		}
	rebuilt, held = [], []
	for index, (employee, day) in enumerate(ordered, start=1):
		entry = {"employee": employee, "date": str(day)}
		reason = _protection(employee, day, True)
		if reason:
			held.append({**entry, "reason": reason, "hr": True})
			continue
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			_lock_employee(employee)
			result = _guarded_rebuild(employee, day)
		except Exception as exc:
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			logger.exception("[erp_backfill] %s on %s could not be rebuilt", employee, day)
			held.append({**entry, "reason": f"rebuild failed: {exc}", "hr": True})
			continue
		if result.get("held"):
			held.append({**entry, "reason": result["held"], "hr": result.get("hr", True)})
		else:
			rebuilt.append({**entry, "marked": result.get("marked") or []})
		if index % COMMIT_EVERY == 0:
			# The commit releases the instance lock; take it again or stop here.
			frappe.db.commit()
			if index < len(ordered) and not _lock(instance):
				held.extend(
					{"employee": e, "date": str(d), "reason": "sync running, skipped", "hr": False}
					for e, d in ordered[index:]
				)
				break
	frappe.db.commit()
	logger.info("[erp_backfill] rebuilt %d day(s), held %d", len(rebuilt), len(held))
	return {"rebuilt": rebuilt, "held_back": held}


def _outcome(dry_run=True, planned=None, inserted=None, held=None, note=None, **extra) -> dict:
	logger.debug("[erp_backfill] outcome: dry_run=%s note=%s", dry_run, note)
	return {
		"dry_run": dry_run,
		"planned": planned or [],
		"inserted": inserted or [],
		"held_back": held or [],
		"already_imported": 0,
		"rebuilt": [],
		"note": note,
		**extra,
	}


def _insert_all(planned, instance: str) -> dict:
	"""Insert the planned punches, one savepoint each, a commit per COMMIT_EVERY —
	and the instance lock taken again after every commit, because the commit
	releases it and a sync starting meanwhile must win."""
	inserted, held, already = [], [], 0
	for index, entry in enumerate(planned, start=1):
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			name = _insert(entry, instance)
		except Exception as exc:
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			if is_source_key_duplicate(exc):
				already += 1
				logger.info("[erp_backfill] %s was imported already", entry["remote_name"])
				continue
			logger.exception("[erp_backfill] %s could not be copied", entry["remote_name"])
			held.append({**entry, "reason": f"could not be inserted: {exc}", "hr": True})
			continue
		if name is None:
			# The same second is already on the hub: nothing was written, so
			# nothing may be reported as written (insert_source_punch's own
			# best-effort re-check).
			already += 1
			logger.info("[erp_backfill] %s is already here; not inserted", entry["remote_name"])
			continue
		inserted.append({**entry, "checkin": name})
		if index % COMMIT_EVERY == 0:
			frappe.db.commit()
			if index < len(planned) and not _lock(instance):
				held.extend({**e, "reason": "sync running, skipped", "hr": False} for e in planned[index:])
				break
	frappe.db.commit()
	logger.info(
		"[erp_backfill] inserted %d punch(es), held %d, already here %d", len(inserted), len(held), already
	)
	return {"inserted": inserted, "held_back": held, "already_imported": already}


def backfill_punches(from_date, to_date, employees=None, dry_run=1) -> dict:
	"""Copy the ERP's pre-cutover punches this hub is missing, then rebuild those days.

	Insert-only and source-keyed: the unique index on `source_checkin` makes a
	second copy impossible, and nothing here updates or deletes anything, on
	either side. Background-safe: it never raises — every refusal is a note or a
	held-back line for HR.
	"""
	apply = not wants_dry_run(dry_run)
	try:
		start, end = resolve_window(from_date, to_date)
	except ValueError as exc:
		logger.warning("[erp_backfill] refused: %s", exc)
		return _outcome(not apply, note=str(exc))
	try:
		if not _enabled():
			return _outcome(not apply, note=f"switched off in HR Settings ({SWITCH})")
		instance = _source_instance()
		if not instance:
			return _outcome(not apply, note="no single enabled ERP instance with credentials")
		if _sync_running(instance):
			return _outcome(not apply, note="sync running, skipped", instance=instance)
		scope = _employees_in_scope(instance, pilot_employees(_pilot_text(), employees))
		hub = _hub_punches(scope, start, end)
		client = _client(instance)
		planned, refused, seen = [], [], {}
		for employee in scope:
			found, dropped = plan_backfill(
				employee, _erp_punches(client, employee, start, end), hub.get(employee, []), start, end
			)
			refused.extend(dropped)
			for entry in found:
				key = (entry["employee"], entry["date"])
				# One protection read per employee-day, not per punch: it takes a
				# row lock, and several punches of one day ask the same question.
				if key not in seen:
					seen[key] = _protection(entry["employee"], getdate(entry["date"]), apply)
				reason = seen[key]
				if reason:
					refused.append({**entry, "reason": reason, "hr": True})
				else:
					planned.append(entry)
		if not apply:
			logger.info("[erp_backfill] dry run %s..%s: %d to copy", start, end, len(planned))
			return _outcome(True, planned=planned, held=refused, instance=instance)
		if not _lock(instance):
			return _outcome(False, note="another import holds the lock, skipped", instance=instance)
		written = _insert_all(planned, instance)
		days = {(entry["employee"], getdate(entry["date"])) for entry in written["inserted"]}
		rebuild = rebuild_days(sorted(days, key=lambda pair: (pair[1], pair[0])), instance) if days else {}
	except Exception as exc:
		logger.exception("[erp_backfill] run crashed")
		return _outcome(not apply, note=f"the copy stopped: {exc}")
	logger.info(
		"[erp_backfill] %s..%s: %d copied, %d rebuilt",
		start,
		end,
		len(written["inserted"]),
		len(rebuild.get("rebuilt") or []),
	)
	return {
		"dry_run": False,
		"instance": instance,
		"window": {"from_date": str(start), "to_date": str(end)},
		"planned": planned,
		"inserted": written["inserted"],
		"already_imported": written["already_imported"],
		"held_back": refused + written["held_back"] + (rebuild.get("held_back") or []),
		"rebuilt": rebuild.get("rebuilt") or [],
		"note": None,
	}
