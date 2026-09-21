"""Source-ERP punches into this hub after cutover — add-only.

OWNER DECISION (14 September 2026): staff still punch on the source ERP after
cutover. Those punches come into this hub, add-only, safe on a working day, and
count toward attendance. Old gaps are filled after a dry run the owner reviews.

WHY NOT THE MIRROR

`hrms.sync.runner._write_row` upserts on the source's document name. Both sites
number Employee Checkin `EMP-CKIN-.MM.-.YYYY.-.######` from their own counters,
so a source name routinely names a different punch here — that upsert is how
staff punches on this site were overwritten in September 2026
(`hrms.sync.checkin_recovery`). After cutover this hub numbers and writes
punches itself, so the name-keyed mirror cannot be the path.

WHAT THIS PATH DOES, AND NEVER DOES

* A punch is (employee, time to the second, log_type) —
  `missing_checkins.diff_punches` — never its name.
* A source punch with no match here is INSERTED under this hub's own autoname,
  with `source_checkin` = "<instance>::<its name on the source>". No name is
  forced, so the naming counter is never touched and a staff punch saved in the
  same instant cannot collide with it.
* A source punch lands at most ONCE, and the DATABASE guarantees it:
  `source_checkin` carries a UNIQUE index. Two importers racing — the sync's
  pass and a manual import, or two workers — cannot both insert it; the loser
  gets a duplicate-key error on that index, which is counted as already
  imported. Local punches leave the field NULL, which the index admits any
  number of times. The instance row lock only saves wasted work; the plan and
  the pre-insert re-check read a transaction snapshot and are best effort.
* Nothing existing is updated or deleted. A re-run matches what the last run
  inserted and writes nothing; a punch HR has since corrected is still
  recognised by its `source_checkin`.
* The imported punch carries NO provenance stamp. The hourly attendance job,
  the stale-IN sweeper and the write-block all read a stamped punch as another
  site's, so a stamped import would be locked AND left out of attendance.
* The shift is resolved here (`fetch_shift`, this hub's rule). The checks that
  exist for a phone punch — geofence, required coordinates, active employee,
  the duplicate-time refusal — are skipped with `ignore_validate`, exactly as
  `checkin_recovery._insert_recovered` does: the source ERP already accepted
  the punch, it has no coordinates and no approver, and the duplicate check is
  done here on the natural key. `resolve_punch_type` and
  `leaves_consecutive_outs` live in the phone API, not in validate, so the
  source's log type is kept as recorded.
* A source punch at a second where this hub holds the OTHER log type is
  refused and named (`contested`), not inserted: one of the two is wrong, and
  only a person can say which.

The pull reads a window of punch TIME (the last `DEFAULT_WINDOW_DAYS` days), not
the run watermark on `modified`, so a punch keyed late on the source, or one a
failed run missed, is still picked up while it is inside the window.
"""

import json
import logging
from collections import Counter
from datetime import date, timedelta

import frappe
from frappe import _

from hrms.sync.missing_checkins import (
	DEFAULT_WINDOW_DAYS,
	DOCTYPE,
	LOCAL_SLACK,
	MAX_SAMPLE,
	MAX_WINDOW_DAYS,
	_remote_scope,
	_resolve_instance,
	_to_date,
	diff_punches,
	fetch_remote_punches,
	is_past_midnight,
	local_employees,
	resolve_window,
)
from hrms.utils.dry_run import wants_dry_run

logger = logging.getLogger(__name__)

#: The punch's name on the source ERP. Created by
#: `runner.get_provenance_custom_fields` as `SOURCE_CHECKIN_FIELD`; a test pins
#: the two literals together so this module needs no runner import.
SOURCE_FIELD = "source_checkin"
PROVENANCE_FIELD = "synced_from_instance"
#: One row's insert rolls back alone; the run commits per doctype.
ROW_SAVEPOINT = "hrms_checkin_import_row"
#: Joins the instance and the source's punch name in `source_checkin`. Source
#: names are unique only per source, and two instances can issue the same one.
SOURCE_KEY_SEPARATOR = "::"
#: MariaDB's duplicate-key error number.
ER_DUP_ENTRY = 1062
REMARK_SAVEPOINT = "hrms_checkin_import_remark"
MAX_NAMES_REPORTED = 10
#: `IN` lists longer than this are split into several local queries.
LOOKUP_CHUNK = 500
#: Days one `remark_attendance` PREVIEW reads in a request. The apply path is
#: not offered here (F6, 21 Sep 2026): the guarded rebuild runs nightly, Fix Day
#: corrects one day under lock, guard and log.
MAX_REMARK_DAYS = 500


# --- pure ---------------------------------------------------------------------


def _flag(value) -> int:
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0


def source_key(instance_name: str, remote_name: str) -> str:
	"""The globally unique `source_checkin` value for one source punch. Pure."""
	return f"{instance_name}{SOURCE_KEY_SEPARATOR}{remote_name}"


def is_source_key_duplicate(error) -> bool:
	"""True only for a duplicate-key error on the `source_checkin` index: that
	source punch is already here. Pure.

	Frappe raises `UniqueValidationError(doctype, name, <IntegrityError>)` for a
	unique index and `DuplicateEntryError` for the primary key. Anything but OUR
	index — the autoname's primary key above all — is a real failure: calling it
	"already imported" would drop a punch without a trace.
	"""
	cause = (
		error.args[-1] if getattr(error, "args", None) and isinstance(error.args[-1], Exception) else error
	)
	args = getattr(cause, "args", ()) or ()
	return len(args) > 1 and args[0] == ER_DUP_ENTRY and str(args[1]).rstrip().endswith(f"'{SOURCE_FIELD}'")


def attendance_day(entry) -> date:
	"""The attendance day a punch most likely belongs to. An OUT before
	`PAST_MIDNIGHT_HOUR` closes the previous day's shift. An estimate for the dry
	run; the real day is the shift `fetch_shift` resolves on insert."""
	moment = entry["time"]
	day = moment.date()
	return day - timedelta(days=1) if is_past_midnight(entry.get("log_type"), moment) else day


def left_before(employee: dict, entry: dict) -> bool:
	"""A Left employee's punch dated after their relieving date. Pure."""
	relieving = employee.get("relieving_date")
	left = (
		employee.get("status") == "Left" and bool(relieving) and _to_date(relieving) < attendance_day(entry)
	)
	if left:
		logger.info(
			"[checkin_import] %s left on %s; punch at %s refused", entry["employee"], relieving, entry["time"]
		)
	return left


def plan_import(remote_rows, local_rows, local_employees) -> dict:
	"""What an append-only import does with these rows. Pure.

	`local_employees` maps each hub Employee a source punch may land on to its
	{status, relieving_date} — `missing_checkins.local_employees`, which admits
	only employees stamped from THIS instance. A hub-native employee can hold the
	same `HR-EMP-*` name as a source employee and be a different person, so a
	name alone is never enough; anything else is counted in `unmapped`.

	`refused` carries a `reason`: `type_mismatch` (the hub holds the other log
	type at that second) or `left` (dated after the employee's relieving date).
	"""
	if not isinstance(local_employees, dict):
		local_employees = {name: {} for name in local_employees}
	mapped, unmapped = [], Counter()
	for row in remote_rows:
		if row.get("employee") in local_employees:
			mapped.append(row)
		else:
			unmapped[row.get("employee")] += 1

	diff = diff_punches(mapped, local_rows)
	insert, refused = [], [{**entry, "reason": "type_mismatch"} for entry in diff["type_mismatch"]]
	for entry in diff["missing"]:
		if left_before(local_employees[entry["employee"]] or {}, entry):
			refused.append({**entry, "reason": "left"})
		else:
			insert.append(entry)
	return {
		"matched": diff["matched"],
		"insert": insert,
		"already_imported": [],
		"refused": refused,
		"unmapped": dict(sorted(unmapped.items(), key=lambda item: str(item[0]))),
	}


def drop_already_imported(plan: dict, imported: dict, instance_name: str) -> dict:
	"""Take out every planned insert a hub punch already records as its source.
	`imported` maps a `source_key` to the local punch. Pure."""
	insert, already = [], list(plan["already_imported"])
	for entry in plan["insert"]:
		local_name = imported.get(source_key(instance_name, entry["remote_name"]))
		if local_name:
			already.append({**entry, "local_name": local_name})
		else:
			insert.append(entry)
	return {**plan, "insert": insert, "already_imported": already}


def drop_deleted_here(plan: dict, deleted_keys, instance_name: str) -> dict:
	"""Refuse every planned insert HR already deleted here, reason `deleted_here`:
	a deletion on the hub is a decision the next pull must not undo. Pure."""
	insert, refused = [], list(plan["refused"])
	for entry in plan["insert"]:
		if source_key(instance_name, entry["remote_name"]) in deleted_keys:
			refused.append({**entry, "reason": "deleted_here"})
		else:
			insert.append(entry)
	return {**plan, "insert": insert, "refused": refused}


def sync_window(today: date, last_completed=None) -> tuple[tuple[date, date], str | None]:
	"""The sync pass's punch window and, when it cannot reach back far enough, the
	note naming the dates it did not read. Pure.

	It reaches a day before the last Completed run started (the default 14 days
	when that is nearer), so a skipped weekend loses no punch; past
	MAX_WINDOW_DAYS it reads the capped window and says what is left uncovered.
	"""
	default_start = today - timedelta(days=DEFAULT_WINDOW_DAYS - 1)
	if last_completed is None:
		return (default_start, today), (
			f"punches before {default_start} were not read automatically: no completed sync is on record; "
			f"run import_missing_checkins for any earlier dates that matter (dry run first)"
		)
	last = _to_date(last_completed)
	wanted = min(default_start, last - LOCAL_SLACK)
	floor = today - timedelta(days=MAX_WINDOW_DAYS - 1)
	if wanted >= floor:
		return (wanted, today), None
	return (floor, today), (
		f"punches before {floor} were not read automatically: the last completed sync started {last}; "
		f"run import_missing_checkins for {wanted}..{floor - timedelta(days=1)} "
		f"(dry run first, at most {MAX_WINDOW_DAYS} days per call)"
	)


def parse_employee_days(value) -> list[tuple[str, date]]:
	"""[(employee, date)] from JSON or a list of pairs / {employee, attendance_date}."""
	if isinstance(value, str):
		value = json.loads(value)
	days = []
	for item in value or []:
		if isinstance(item, dict):
			employee, day = item.get("employee"), item.get("attendance_date")
		else:
			employee, day = item
		if not isinstance(employee, str) or not employee or not day:
			raise ValueError(f"not an (employee, attendance_date) pair: {item!r}")
		days.append((employee, _to_date(day)))
	return list(dict.fromkeys(days))


def plan_remark(punches, attendance_rows, removed=False) -> tuple[str, str]:
	"""What re-marking one employee-day would do, before any payout check. Pure.

	`punches` are the day's unstamped punches that carry a shift; `attendance_rows`
	its non-cancelled Attendance. A row the automation does not own — a draft,
	HR's hand-marked row, a leave, another instance's — is never rebuilt here, the
	same rule `shift_type.get_automation_attendance` applies. `removed`: HR
	removed the day in Shift Attendance (hrms.utils.hr_removed_day).
	"""
	if removed:
		return "hr-owned", "HR removed this day in Shift Attendance"
	if not punches:
		return "nothing-to-mark", "no punch on this day carries a shift"
	for row in attendance_rows:
		if _flag(row.get("docstatus")) == 0:
			return "hr-owned", f"{row.get('name')} is a draft"
		if (
			not _flag(row.get("auto_attendance"))
			or row.get("leave_type")
			or row.get("status") == "On Leave"
			or _flag(row.get("modify_half_day_status"))
			or row.get(PROVENANCE_FIELD)
		):
			return "hr-owned", f"{row.get('name')} is marked by hand, a leave, or another instance's"
	if not any(not p.get("attendance") and not _flag(p.get("skip_auto_attendance")) for p in punches):
		stuck = stuck_row(attendance_rows, punches)
		if stuck:
			# E21 (15 Sep 2026): a Half Day row whose OUT was already linked read
			# "up to date" forever. Two live taps and a broken row is a day to rebuild.
			return "remark", (
				f"{stuck.get('name')} reads {stuck.get('status')} with {live_count(punches)} live taps: "
				"rebuilt from all of them"
			)
		return "up-to-date", "every punch is already linked to its attendance"
	return "remark", ""


def pending_late_outs(rows) -> set:
	"""Names of the rows that are forgotten check-outs still waiting for their
	approver (E16). One read of Remote Checkin Request, only for Pending rows."""
	from hrms.hr.doctype.shift_type.shift_type import pending_late_checkouts

	return pending_late_checkouts([r for r in rows if r.get("name")])


def without_pending_late_outs(rows) -> list:
	"""E16 / C1 (integration review, 15 Sep 2026): a forgotten check-out filed late
	is a CLAIM until its approver says yes — neither evidence nor a live tap. Only
	`ShiftType.get_employee_checkins` dropped it; every recovery read that hands
	rows to `shift_day_result` goes through here so a Pending late OUT cannot
	make a Half Day row "stuck" and re-mark it Present. An approved one counts."""
	late = pending_late_outs(rows)
	if not late:
		return list(rows)
	logger.info(
		"[checkin_import] %d pending late check-out(s) wait for approval: %s", len(late), sorted(late)
	)
	return [r for r in rows if r.get("name") not in late]


def live_count(punches) -> int:
	"""Taps the engine would count: not skipped, not rejected. Pure."""
	return sum(
		1
		for p in punches
		if not _flag(p.get("skip_auto_attendance")) and p.get("remote_approval_status") != "Rejected"
	)


def stuck_row(attendance_rows, punches):
	"""The submitted row that reads Half Day / no out time / 0 h while at least two
	live taps exist for the day, or None. Pure. One live tap is a lone IN: HR's
	(owner ruling), never rebuilt here."""
	if live_count(punches) < 2:
		return None
	for row in attendance_rows:
		if _flag(row.get("docstatus")) != 1:
			continue
		if (
			row.get("status") == "Half Day"
			or not row.get("out_time")
			or not float(row.get("working_hours") or 0)
		):
			return row
	return None


# --- reads ----------------------------------------------------------------------


def _lock_instance(instance_name: str) -> bool:
	"""Take the HRMS ERP Instance row lock WITHOUT waiting; False when another
	punch import holds it. A COURTESY, held until this transaction ends, so two
	importers rarely do the same work at once. It guarantees nothing about
	duplicates — the unique index on `source_checkin` does.

	Raw SQL, so no metadata read (a cold doctype cache) runs ahead of it."""
	try:
		frappe.db.sql(
			"select name from `tabHRMS ERP Instance` where name=%s for update nowait", (instance_name,)
		)
	except frappe.QueryTimeoutError:
		logger.warning("[checkin_import] %s: another punch import holds the lock", instance_name)
		return False
	return True


def _local_punches(employees, window) -> list:
	"""Hub punches for these employees, a day past each edge of the window."""
	if not employees:
		return []
	return frappe.get_all(
		DOCTYPE,
		filters={
			"employee": ["in", list(employees)],
			"time": [
				"between",
				[(window[0] - LOCAL_SLACK).isoformat(), (window[1] + LOCAL_SLACK).isoformat()],
			],
		},
		fields=["name", "employee", "time", "log_type"],
		order_by="time asc",
	)


def _last_completed_start(instance_name: str):
	"""When the last Completed run for this instance started — `runner.get_watermark`'s
	query, repeated so this module needs no runner import. Keep the two in step: a
	different anchor would let the punch window and the mirror disagree."""
	last = frappe.get_all(
		"HRMS Sync Run",
		filters={"source_instance": instance_name, "status": "Completed"},
		fields=["started_at"],
		order_by="started_at desc",
		limit=1,
	)
	return last[0]["started_at"] if last else None


def _deleted_source_keys(instance_name: str, window) -> set:
	"""`source_key`s of this instance's imported punches HR deleted on the hub and
	has not restored. One query: a punch in the window was deleted after its punch
	time, so no older Deleted Document can hold one. The LIKE only narrows; the
	parsed `source_checkin` decides, so a deleted local punch never counts."""
	prefix = source_key(instance_name, "")
	rows = frappe.get_all(
		"Deleted Document",
		filters={
			"deleted_doctype": DOCTYPE,
			"restored": 0,
			"creation": [">=", (window[0] - LOCAL_SLACK).isoformat()],
			"data": ["like", f"%{prefix}%"],
		},
		fields=["data"],
	)
	keys = set()
	for row in rows:
		try:
			data = json.loads(row.get("data") or "{}")
		except ValueError:
			logger.warning("[checkin_import] unreadable Deleted Document data for %s; ignored", instance_name)
			continue
		key = data.get(SOURCE_FIELD) if isinstance(data, dict) else None
		if isinstance(key, str) and key.startswith(prefix):
			keys.add(key)
	logger.info(
		"[checkin_import] %s: %s imported punch(es) deleted here since %s",
		instance_name,
		len(keys),
		window[0],
	)
	return keys


def _imported_keys(entries, instance_name: str) -> dict:
	"""`source_key` -> hub punch, for punches imported earlier. Saves work; the
	unique index, not this read, is what stops a second copy."""
	keys = sorted({source_key(instance_name, entry["remote_name"]) for entry in entries})
	found = {}
	for start in range(0, len(keys), LOOKUP_CHUNK):
		for row in frappe.get_all(
			DOCTYPE,
			filters={SOURCE_FIELD: ["in", keys[start : start + LOOKUP_CHUNK]]},
			fields=["name", SOURCE_FIELD],
		):
			found.setdefault(row.get(SOURCE_FIELD), row.get("name"))
	logger.debug("[checkin_import] %s of %s planned punch(es) already imported", len(found), len(keys))
	return found


def _plan(remote_rows, window, instance_name: str) -> dict:
	employees = local_employees(instance_name)
	mapped = sorted({row.get("employee") for row in remote_rows if row.get("employee") in employees})
	plan = plan_import(remote_rows, _local_punches(mapped, window), employees)
	plan = drop_already_imported(plan, _imported_keys(plan["insert"], instance_name), instance_name)
	plan = drop_deleted_here(plan, _deleted_source_keys(instance_name, window), instance_name)
	logger.info(
		"[checkin_import] %s..%s: remote=%s matched=%s insert=%s already_imported=%s refused=%s unmapped=%s",
		window[0],
		window[1],
		len(remote_rows),
		plan["matched"],
		len(plan["insert"]),
		len(plan["already_imported"]),
		len(plan["refused"]),
		len(plan["unmapped"]),
	)
	return plan


def _attendance_days(entries) -> list:
	"""The (employee, day) pairs these punches touch that already hold Attendance.

	Keyed by `attendance_day`, not the punch's calendar date: a 01:04 OUT belongs
	to the day before, and `checkin_recovery._attendance_by_day` (calendar date)
	would name the wrong day for it.
	"""
	days = sorted({(entry["employee"], attendance_day(entry)) for entry in entries})
	if not days:
		return []
	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", sorted({employee for employee, _day in days})],
			"attendance_date": [
				"between",
				[min(day for _e, day in days).isoformat(), max(day for _e, day in days).isoformat()],
			],
			"docstatus": ["!=", 2],
		},
		fields=[
			"name",
			"employee",
			"attendance_date",
			"status",
			"docstatus",
			"auto_attendance",
			"leave_type",
		],
		order_by="docstatus desc",
	)
	by_day: dict[tuple, list] = {}
	for row in rows:
		by_day.setdefault((row.get("employee"), _to_date(row.get("attendance_date"))), []).append(
			{
				"name": row.get("name"),
				"status": row.get("status"),
				"docstatus": row.get("docstatus"),
				"auto_attendance": row.get("auto_attendance"),
				"leave_type": row.get("leave_type"),
			}
		)
	return [
		{"employee": employee, "attendance_date": day.isoformat(), "attendance": by_day[(employee, day)]}
		for employee, day in days
		if (employee, day) in by_day
	]


def _sample(entry: dict) -> dict:
	row = {
		"employee": entry["employee"],
		"time": entry["time"].strftime("%Y-%m-%d %H:%M:%S"),
		"log_type": entry["log_type"],
		"remote_name": entry["remote_name"],
		"device_id": entry.get("device_id"),
		"attendance_day": attendance_day(entry).isoformat(),
	}
	if entry.get("reason"):
		row["reason"] = entry["reason"]
	if "local_log_type" in entry:
		row.update(local_log_type=entry["local_log_type"], local_name=entry["local_name"])
	return row


# --- the write --------------------------------------------------------------------


def insert_source_punch(entry: dict, instance_name: str) -> str | None:
	"""Insert ONE new, unstamped Employee Checkin for a source punch. Never
	updates anything; the name comes from this hub's autoname.

	None when a punch with the same natural key is visible here — a best-effort
	re-check, since `ignore_validate` skips the controller's own duplicate check
	and this read sees the transaction's snapshot. A second copy of the SAME
	source punch is refused by the unique index instead (see `_insert_all`)."""
	present = frappe.db.exists(
		DOCTYPE,
		{
			"employee": entry["employee"],
			"time": entry["time"],
			"log_type": entry["log_type"] or ["is", "not set"],
		},
	)
	if present:
		logger.info("[checkin_import] %s is already here as %s; not inserted", entry["remote_name"], present)
		return None
	doc = frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"employee": entry["employee"],
			"time": entry["time"],
			"log_type": entry["log_type"] or None,
			"device_id": entry.get("device_id"),
			SOURCE_FIELD: source_key(instance_name, entry["remote_name"]),
		}
	)
	doc.flags.ignore_permissions = True
	# Phone-punch checks (geofence, coordinates, active employee, duplicate time)
	# do not apply to a punch the source ERP already recorded; see module docstring.
	doc.flags.ignore_validate = True
	doc.insert()
	# The shift fields the hourly job filters on, resolved the way "Fetch Shifts"
	# does — after insert, as checkin_recovery does, so an OUT finds its IN.
	doc.fetch_shift()
	doc.flags.ignore_validate = True
	doc.save()
	# The punch went in with no shift, so after_insert's session restamp had
	# nothing to anchor on, and save() does not fire after_insert. Run it now
	# that the shift is stored: an imported IN arriving after its later punches
	# pulls them onto its session. One read per punch; mirrored and
	# attendance-linked punches are never rewritten (see the override).
	restamp = getattr(doc, "_restamp_later_session_punches", None)
	if restamp:
		restamp()
	logger.info(
		"[checkin_import] inserted %s for %s at %s %s from source %s",
		doc.name,
		entry["employee"],
		entry["time"],
		entry["log_type"],
		entry["remote_name"],
	)
	return doc.name


def _insert_all(entries, instance_name: str) -> dict:
	"""Insert each planned punch under its own savepoint; one failure costs one row.

	A duplicate-key error on `source_checkin` means another importer landed that
	punch first: rolled back to the savepoint (so the batch goes on) and counted
	in `already_imported`, never as an error and never as a second row.
	"""
	inserted, row_errors, errored, skipped, already = [], [], 0, 0, 0
	for entry in entries:
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			name = insert_source_punch(entry, instance_name)
			if name:
				inserted.append(name)
			else:
				skipped += 1
		except Exception as e:  # one bad row must not lose the rest
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			if is_source_key_duplicate(e):
				already += 1
				# Frappe queued a "must be unique" message for the user; it is not one.
				from frappe.utils.messages import clear_last_message

				clear_last_message()
				logger.info(
					"[checkin_import] %s was imported concurrently; not inserted", entry["remote_name"]
				)
				continue
			errored += 1
			if len(row_errors) < MAX_NAMES_REPORTED:
				row_errors.append(f"{entry['remote_name']}: {e}")
			logger.error(
				"[checkin_import] %s for %s at %s not inserted: %s",
				entry["remote_name"],
				entry["employee"],
				entry["time"],
				e,
			)
	return {
		"inserted": inserted,
		"errored": errored,
		"row_errors": row_errors,
		"skipped": skipped,
		"already_imported": already,
	}


def import_source_checkins(client, instance_name: str, today=None) -> dict:
	"""The run's Employee Checkin pass after cutover. Result shaped like
	`runner.sync_doctype`'s, so the run totals read it unchanged.

	Nothing this pass leaves unwritten counts against the run. Every punch inside
	the window is re-read on the next run anyway, and holding the ONE shared
	watermark for a punch would force a wide re-pull of every mirrored doctype
	over hub edits. So `orphaned`, `errored` and `contested` stay 0, and what was
	not written — unmapped employees, refused punches, failed inserts, or the
	whole pass when a manual import holds the lock — is in `outcomes`, counts and
	a sample, for the run record.
	"""
	if today is None:
		from frappe.utils import getdate

		today = getdate()
	last_completed = _last_completed_start(instance_name)
	window, uncovered = sync_window(today, last_completed)
	logger.info(
		"[checkin_import] %s: window %s..%s (last completed sync started %s)%s",
		instance_name,
		window[0],
		window[1],
		last_completed or "never",
		" — " + uncovered if uncovered else "",
	)
	outcomes = {
		"unmapped": 0,
		"refused": 0,
		"deleted_here": 0,
		"insert_errors": 0,
		"busy": False,
		"sample": [],
	}
	result = {
		"doctype": DOCTYPE,
		"pulled": 0,
		"written": 0,
		"inserted": 0,
		"updated": 0,
		"skipped": 0,
		"errored": 0,
		"orphaned": 0,
		"contested": 0,
		"contested_names": [],
		"missing_parents": [],
		# Recorded in the run's error log, never counted: the run stays Completed.
		"row_errors": [uncovered] if uncovered else [],
		"dropped_fields": [],
		"schema_gaps": [],
		"window": {"from_date": window[0].isoformat(), "to_date": window[1].isoformat()},
		"outcomes": outcomes,
	}
	remote_rows = fetch_remote_punches(client, window, _remote_scope(client, instance_name, None))
	result["pulled"] = len(remote_rows)
	# A courtesy: another import is already doing this work. Duplicates are the
	# unique index's job, not this lock's.
	if not _lock_instance(instance_name):
		outcomes["busy"] = True
		return result

	plan = _plan(remote_rows, window, instance_name)
	outcome = _insert_all(plan["insert"], instance_name)
	inserted = len(outcome["inserted"])
	# A hub delete is a settled decision (Nabil, 14 Sep 2026): counted, never sampled,
	# so it cannot crowd the unmapped and refused lines that need someone out of the
	# ten-line error log for the weeks it stays inside the window.
	deleted_here = [entry for entry in plan["refused"] if entry.get("reason") == "deleted_here"]
	refused = [entry for entry in plan["refused"] if entry.get("reason") != "deleted_here"]
	outcomes.update(
		unmapped=sum(plan["unmapped"].values()),
		refused=len(refused),
		deleted_here=len(deleted_here),
		insert_errors=outcome["errored"],
		sample=(
			[
				f"refused {entry['remote_name']} ({entry['reason']}) for {entry['employee']} at {entry['time']}"
				for entry in refused
			]
			+ [f"unmapped {employee}: {count} punch(es)" for employee, count in plan["unmapped"].items()]
			+ outcome["row_errors"]
		)[:MAX_NAMES_REPORTED],
	)
	result.update(
		written=inserted,
		inserted=inserted,
		skipped=plan["matched"]
		+ len(plan["already_imported"])
		+ outcome["skipped"]
		+ outcome["already_imported"],
	)
	logger.info(
		"[checkin_import] %s %s..%s: pulled=%s inserted=%s skipped=%s unmapped=%s refused=%s deleted_here=%s insert_errors=%s",
		instance_name,
		window[0],
		window[1],
		result["pulled"],
		inserted,
		result["skipped"],
		outcomes["unmapped"],
		outcomes["refused"],
		outcomes["deleted_here"],
		outcomes["insert_errors"],
	)
	return result


# --- the heal: dry run first ------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def import_missing_checkins(instance: str | None = None, from_date=None, to_date=None, dry_run=1) -> dict:
	"""Fill old gaps: source punches in [from_date, to_date] missing on this hub.

	Dry run by default: says what it would insert and which days already hold an
	Attendance (with its status and docstatus) that may need `remark_attendance`.
	`dry_run=0` inserts punches only, through the same append-only path as the
	pull — attendance is never touched here.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("import punches across the whole source instance"))

	from frappe.utils import cint, getdate

	from hrms.sync.client import RemoteInstanceClient, RemoteInstanceError

	dry_run = wants_dry_run(dry_run)
	try:
		window = resolve_window(from_date, to_date, getdate())
	except ValueError as e:
		frappe.throw(str(e))

	instance = _resolve_instance(instance)
	try:
		client = RemoteInstanceClient(instance)
		remote_rows = fetch_remote_punches(client, window, _remote_scope(client, instance, None))
	except RemoteInstanceError as e:
		logger.warning("[checkin_import] cannot read source %s: %s", instance, e)
		frappe.throw(_("Cannot read punches from {0}: {1}").format(instance, e))

	if not dry_run:
		# Courtesies, both: they spare HR a run that would only find the punches
		# already landing. The unique index on `source_checkin` is what makes a
		# second copy impossible when they miss.
		if not _lock_instance(instance):
			frappe.throw(
				_("Another punch import for {0} is in progress; try again shortly.").format(instance)
			)
		from hrms.sync.runner import running_run

		run = running_run(instance)
		if run:
			frappe.throw(
				_("Sync {0} from {1} is running; import punches once it has finished.").format(run, instance)
			)

	plan = _plan(remote_rows, window, instance)
	result = {
		"instance": instance,
		"window": {"from_date": window[0].isoformat(), "to_date": window[1].isoformat()},
		"dry_run": bool(dry_run),
		"remote_rows": len(remote_rows),
		"matched": plan["matched"],
		"to_insert": len(plan["insert"]),
		"already_imported": len(plan["already_imported"]),
		"refused": len(plan["refused"]),
		"deleted_here": sum(1 for entry in plan["refused"] if entry.get("reason") == "deleted_here"),
		"unmapped_employees": [
			{"employee": employee, "remote_punches": count} for employee, count in plan["unmapped"].items()
		],
		"inserts": [_sample(entry) for entry in plan["insert"][:MAX_SAMPLE]],
		"refused_sample": [_sample(entry) for entry in plan["refused"][:MAX_SAMPLE]],
		"attendance_days": _attendance_days(plan["insert"]),
	}
	if dry_run:
		logger.info(
			"[checkin_import] dry run by %s on %s: %s to insert, %s day(s) already hold attendance",
			frappe.session.user,
			instance,
			result["to_insert"],
			len(result["attendance_days"]),
		)
		return result

	outcome = _insert_all(plan["insert"], instance)
	result.update(
		inserted=len(outcome["inserted"]),
		errored=outcome["errored"],
		row_errors=outcome["row_errors"],
		already_imported=result["already_imported"] + outcome["already_imported"],
	)
	logger.info(
		"[checkin_import] applied by %s on %s: inserted=%s errored=%s",
		frappe.session.user,
		instance,
		result["inserted"],
		result["errored"],
	)
	return result


def _financially_locked(employee, day, attendance, for_update: bool):
	"""The payout a day's rebuild would contradict (submitted Salary Slip,
	approved OT Request, Overtime Details), or None. The hub's own guard."""
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	return _repair_financial_dependency(employee, day, attendance, for_update=for_update)


def _same_engine_result(result, shift_name) -> bool:
	"""Would the engine keep the existing row (same status, hours, in and out)?"""
	from hrms.hr.doctype.employee_checkin.employee_checkin import _same_day_result

	existing = result.get("existing")
	return bool(existing) and _same_day_result(
		existing,
		result.status,
		result.working_hours,
		result.get("in_time"),
		result.get("out_time"),
		shift_name,
	)


def _preview(shift, employee: str, day: date, logs, unchanged: bool = False) -> dict:
	"""The day the hourly job's rule would write, computed without writing
	(`ShiftType.shift_day_result`). OT bands are set by Attendance on insert.
	`unchanged`: also say whether the engine would keep the existing row."""
	if shift.has_incorrect_shift_config():
		return {"shift": shift.name, "status": None, "detail": "auto attendance is off or not configured"}
	result = shift.shift_day_result(employee, day, logs)
	if not result:
		return {"shift": shift.name, "status": None, "detail": "the shift's rules would not mark this day"}
	preview = {
		"shift": shift.name,
		"status": result.status,
		"working_hours": round(float(result.working_hours or 0), 2),
		"in_time": str(result.in_time) if result.in_time else None,
		"out_time": str(result.out_time) if result.out_time else None,
		"late_entry": bool(result.late_entry),
		"early_exit": bool(result.early_exit),
		"overtime_type": result.overtime_type,
		"rebuilds": result.existing.name if result.existing else None,
		"punches": [row.name for row in result.eligible_logs],
	}
	if unchanged:
		preview["unchanged"] = _same_engine_result(result, shift.name)
	logger.info("[checkin_import] preview %s on %s: %s", employee, day, preview)
	return preview


def _remark_day(employee: str, day: date, apply: bool) -> dict:
	"""Plan — and with `apply`, run — the hourly job's own marking for one day."""
	from hrms.hr.doctype.shift_type.shift_type import day_evidence

	iso = day.isoformat()
	# The engine's own loader: mirrored and pending late OUTs left out, a
	# skipped punch KEPT as the wall it is (E-H1, 21 Sep 2026).
	punches = day_evidence(
		{"employee": employee, "shift_start": ["between", [iso, iso]], "shift": ["is", "set"]},
		order_by="time asc",
	)
	attendance = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": iso, "docstatus": ["<", 2]},
		fields=[
			"name",
			"status",
			"docstatus",
			"auto_attendance",
			"leave_type",
			"modify_half_day_status",
			"working_hours",
			"out_time",
			PROVENANCE_FIELD,
		],
	)
	from hrms.utils.hr_removed_day import removed_by_hr

	action, detail = plan_remark(punches, attendance, removed=removed_by_hr(employee, day))
	if action == "remark":
		submitted = next((row.get("name") for row in attendance if _flag(row.get("docstatus")) == 1), None)
		# A preview must not hold Salary Slip row locks while somebody reads it.
		locked = _financially_locked(employee, day, submitted, for_update=apply)
		if locked:
			action, detail = "locked", f"payroll or approved overtime depends on this day ({locked})"

	entry = {
		"employee": employee,
		"attendance_date": iso,
		"action": action,
		"detail": detail,
		"attendance": [
			{"name": row.get("name"), "status": row.get("status"), "docstatus": row.get("docstatus")}
			for row in attendance
		],
		"punches": [row.get("name") for row in punches],
	}
	if action != "remark":
		return entry

	# What the hourly job reads: unlinked punches, a skipped one kept as the wall
	# it is. It then merges the punches already linked to the day's automation
	# row and rebuilds it — cancel, and amend from all of them — or keeps it when
	# nothing changed. A stuck day (E21) has nothing unlinked that counts: its
	# taps linked to this day's submitted rows are handed over instead, and the
	# day is left alone when the engine would mark it the same.
	submitted_rows = {row.get("name") for row in attendance if _flag(row.get("docstatus")) == 1}
	unlinked = [
		row for row in punches if not row.get("attendance") and not _flag(row.get("skip_auto_attendance"))
	]
	stuck = not unlinked
	by_shift: dict[str, list] = {}
	for row in punches:
		if not row.get("attendance") or (stuck and row.get("attendance") in submitted_rows):
			by_shift.setdefault(row.get("shift"), []).append(row)
	shifts = {shift_name: frappe.get_doc("Shift Type", shift_name) for shift_name in by_shift}
	entry["expected"] = [
		_preview(shifts[shift_name], employee, day, logs, unchanged=stuck)
		for shift_name, logs in by_shift.items()
	]
	if stuck and entry["expected"] and all(e.get("unchanged") for e in entry["expected"]):
		entry.update(action="up-to-date", detail="the engine reads the same result: nothing to rebuild")
		logger.info("[checkin_import] %s on %s: engine result unchanged, left as it is", employee, iso)
		return entry
	if not apply:
		return entry

	marked, errors = [], []
	for shift_name, logs in by_shift.items():
		shift = shifts[shift_name]
		if shift.has_incorrect_shift_config():
			errors.append(f"{shift_name}: auto attendance is off or not configured")
			continue
		frappe.db.savepoint(REMARK_SAVEPOINT)
		try:
			result = shift.mark_attendance_for_shift_logs(employee, day, logs)
		except Exception as e:
			frappe.db.rollback(save_point=REMARK_SAVEPOINT)
			errors.append(f"{shift_name}: {e}")
			logger.exception(
				"[checkin_import] re-marking %s on %s under %s failed", employee, iso, shift_name
			)
			continue
		if result:
			marked.append(result.name)
		else:
			errors.append(f"{shift_name}: the shift's rules did not mark this day")
	entry.update(marked=marked, errors=errors)
	logger.info("[checkin_import] re-marked %s on %s: marked=%s errors=%s", employee, iso, marked, errors)
	return entry


@frappe.whitelist(methods=["POST"])
def remark_attendance(employee_days, dry_run=1) -> dict:
	"""Preview what re-marking these (employee, attendance_date) days from their
	punches would do — the hourly job's own rule (`ShiftType.mark_attendance_for_shift_logs`)
	planned, not run. Held: a day HR maintains by hand, a leave, a draft, another
	instance's row, and any day a payout already depends on.

	`dry_run=0` is refused: up to 500 historical days rewritten inline with no
	employee lock, no never-worse guard and no HR Day Fix Log row was the widest
	unguarded write in the domain (F6). The guarded rebuild runs nightly
	(attendance_auto_recovery); one day is corrected with Fix Day.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("re-mark attendance across the whole hub"))

	from frappe.utils import cint

	try:
		days = parse_employee_days(employee_days)
	except (TypeError, ValueError) as e:
		frappe.throw(str(e))
	if len(days) > MAX_REMARK_DAYS:
		frappe.throw(_("{0} days in one call; send at most {1}.").format(len(days), MAX_REMARK_DAYS))

	if not wants_dry_run(dry_run):
		logger.warning(
			"[checkin_import] remark_attendance apply refused for %s (%d day(s)): preview only",
			frappe.session.user,
			len(days),
		)
		frappe.throw(
			_(
				"Apply is not offered here. The guarded rebuild runs nightly; "
				"to correct one day now, press Fix day on that day."
			)
		)
	results = [_remark_day(employee, day, False) for employee, day in days]
	counts = dict(Counter(row["action"] for row in results))
	logger.info("[checkin_import] remark_attendance dry run by %s: %s", frappe.session.user, counts)
	return {"dry_run": True, "counts": counts, "days": results}
