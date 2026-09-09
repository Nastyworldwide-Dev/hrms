"""Recover the punches a sync pull wrote over.

WHAT HAPPENED (verifica-live, first week of September 2026)

Employee Checkin numbers itself `EMP-CKIN-.MM.-.YYYY.-.######` on the source
ERP and on this hub, from two independent counters. The mirror upserts on the
SOURCE's name (`hrms.sync.runner._write_row`), and until `IDENTITY_FIELDS` it let
a source take any unstamped existing row. So when the source issued the same
number for somebody else's punch, the pull replaced employee, time, log type and
coordinates on a row a member of staff had created here, and stamped it
`synced_from_instance`. The hourly attendance job excludes stamped punches, so
the real employee's day read Absent or Half Day and the punch vanished from
their history. Low numbers collide first: the earliest days of the month for
everyone.

WHY IT IS RECOVERABLE

`owner`, `creation` and `modified` are never mirrored (`_UNMIRRORED_FIELDS`), so
an overwritten row still says WHO tapped (owner -> Employee.user_id) and WHEN
(creation, naive wall clock in the SYSTEM timezone; the stored time was the
employee's attendance wall clock, `hrms.utils.timezone.employee_now`). The log
type survives on the Remote Checkin Request the punch raised, if it raised one;
otherwise it is inferred by IN/OUT alternation within that employee's day and
labelled as inferred so HR can see which rows to eyeball.

WHAT THIS DOES AND NEVER DOES

`collect` classifies every punch in a window as local / mirrored / overwritten
and plans one NEW unstamped punch per overwritten row (device_id
"recovered:<name>", idempotent). `recover_overwritten_checkins` is System
Manager only and a dry run unless told otherwise; the apply step inserts those
new rows and touches nothing that exists. The hourly job then marks the days
from them. The overwritten row itself is left as the audit trail.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate

logger = logging.getLogger(__name__)

RECOVERED_PREFIX = "recovered:"
#: A row created this close to a sync run's edges is treated as the run's own insert.
RUN_SLACK = timedelta(minutes=5)
#: A run with no finish time (killed, still marked Running) is assumed this long.
RUN_DEFAULT_LENGTH = timedelta(hours=6)
#: A local punch this close to the true time means the employee re-punched already.
LOCAL_MATCH_TOLERANCE = timedelta(seconds=60)
#: A Remote Checkin Request this close to the true time is the punch's own request.
REQUEST_MATCH_TOLERANCE = timedelta(seconds=120)

LOCAL, MIRRORED, OVERWRITTEN = "local", "mirrored", "overwritten"


# --- pure ---------------------------------------------------------------------


def classify_punch(row: dict, run_windows, employee_of_user: dict, operator_users) -> dict:
	"""local / mirrored / overwritten for one Employee Checkin row.

	`row` needs name, employee, owner, creation, synced_from_instance.
	`run_windows` is an iterable of (started_at, finished_at|None).
	`employee_of_user` maps a User id to its Employee; `operator_users` are the
	users who ran syncs (a mirrored insert is owned by one of them).
	"""
	if not row.get("synced_from_instance"):
		return {"kind": LOCAL, "reason": "", "true_employee": row.get("employee")}

	owner = row.get("owner")
	owners_employee = employee_of_user.get(owner)
	if not owners_employee:
		return {"kind": MIRRORED, "reason": "", "true_employee": None}

	# A mirrored insert is owned by whoever pressed Sync, and that person may
	# well have an Employee record of their own. For an operator only the run
	# window decides; for anyone else a row showing another employee is theirs.
	if owner not in operator_users and owners_employee != row.get("employee"):
		return {
			"kind": OVERWRITTEN,
			"reason": "created by another employee's user",
			"true_employee": owners_employee,
		}
	created = get_datetime(row.get("creation"))
	if not any(_inside(created, start, end) for start, end in run_windows):
		return {
			"kind": OVERWRITTEN,
			"reason": "created outside every sync run",
			"true_employee": owners_employee,
		}
	return {"kind": MIRRORED, "reason": "", "true_employee": None}


def _inside(moment: datetime, start, end) -> bool:
	start = get_datetime(start)
	end = get_datetime(end) if end else start + RUN_DEFAULT_LENGTH
	return start - RUN_SLACK <= moment <= end + RUN_SLACK


def true_punch_time(creation, system_tz: str, attendance_tz: str) -> datetime:
	"""`creation` (naive, system wall clock) as the naive attendance wall clock."""
	moment = get_datetime(creation)
	if system_tz == attendance_tz:
		return moment
	return moment.replace(tzinfo=ZoneInfo(system_tz)).astimezone(ZoneInfo(attendance_tz)).replace(tzinfo=None)


def infer_log_types(punches: list) -> list:
	"""Fill missing log types by alternation for ONE employee's ONE day.

	Each punch is {time, log_type|None, source}. Known types anchor the walk: the
	punch after an IN is expected to be an OUT. A known type from a Remote Checkin
	Request is "request", any other known one "known", a filled one "inferred".
	"""
	ordered = sorted(punches, key=lambda p: get_datetime(p["time"]))
	expected = "IN"
	for punch in ordered:
		if punch.get("log_type"):
			punch["confidence"] = "request" if punch.get("source") == "request" else "known"
		else:
			punch["log_type"] = expected
			punch["confidence"] = "inferred"
		expected = "OUT" if punch["log_type"] == "IN" else "IN"
	return ordered


def plan_recovery(
	overwritten: list,
	requests_by_checkin: dict,
	local_punches: dict,
	already_recovered,
	tz_of_employee,
	system_tz: str,
) -> list:
	"""One plan entry per overwritten row: what to insert, or why not.

	`overwritten` rows carry name, synced_from_instance, creation, true_employee.
	`requests_by_checkin` maps a checkin name to {log_type, checkin_time}.
	`local_punches` maps an employee to its unstamped rows [{name, time, log_type}].
	`tz_of_employee(employee)` returns the attendance timezone.
	"""
	entries = []
	for row in overwritten:
		employee = row["true_employee"]
		moment = true_punch_time(row["creation"], system_tz, tz_of_employee(employee))
		entry = {
			"source_name": row["name"],
			"stamped_from": row.get("synced_from_instance"),
			"employee": employee,
			"time": moment,
			"log_type": None,
			"confidence": None,
			"action": "insert",
		}
		if row["name"] in already_recovered:
			entry["action"] = "skip-already-recovered"
		elif any(
			abs(get_datetime(p["time"]) - moment) <= LOCAL_MATCH_TOLERANCE
			for p in local_punches.get(employee, [])
		):
			entry["action"] = "skip-local-exists"
		request = requests_by_checkin.get(row["name"])
		if request and abs(get_datetime(request["checkin_time"]) - moment) <= REQUEST_MATCH_TOLERANCE:
			entry["log_type"], entry["confidence"] = request["log_type"], "request"
		entries.append(entry)

	_fill_inferred_types(entries, local_punches)
	entries.sort(key=lambda e: (e["employee"] or "", e["time"]))
	logger.info(
		"[checkin_recovery] planned %d rows: %s",
		len(entries),
		{a: sum(1 for e in entries if e["action"] == a) for a in {e["action"] for e in entries}},
	)
	return entries


def _fill_inferred_types(entries: list, local_punches: dict) -> None:
	"""Alternation runs over the employee's whole day: local rows anchor it."""
	days = {}
	for entry in entries:
		days.setdefault((entry["employee"], getdate(entry["time"])), []).append(entry)
	for (employee, day), pending in days.items():
		known = [
			{"time": p["time"], "log_type": p["log_type"], "source": "local"}
			for p in local_punches.get(employee, [])
			if getdate(p["time"]) == day
		]
		candidates = [
			{
				"time": e["time"],
				"log_type": e["log_type"],
				"source": "request" if e["log_type"] else "recovered",
				"entry": e,
			}
			for e in pending
		]
		for punch in infer_log_types(known + candidates):
			entry = punch.get("entry")
			if entry is not None and not entry["log_type"]:
				entry["log_type"], entry["confidence"] = punch["log_type"], punch["confidence"]


# --- frappe -------------------------------------------------------------------


def collect(from_date, to_date, employee: str | None = None) -> dict:
	"""Every punch whose time OR creation falls in the window, classified, with
	the recovery plan and the true employee's attendance for that day."""
	from frappe.utils import get_system_timezone

	from hrms.utils.timezone import get_attendance_timezone

	window_end = get_datetime(add_days(getdate(to_date), 1))
	# No SQL filter on `employee`: an overwritten punch shows somebody else in
	# that column. The employee filter is applied after classification, on the
	# true employee, below.
	rows = frappe.get_all(
		"Employee Checkin",
		or_filters=[
			["time", ">=", getdate(from_date)],
			["creation", ">=", getdate(from_date)],
		],
		fields=[
			"name",
			"employee",
			"employee_name",
			"log_type",
			"time",
			"owner",
			"creation",
			"synced_from_instance",
			"device_id",
			"attendance",
			"shift",
		],
		order_by="creation asc",
		limit_page_length=0,
	)
	rows = [r for r in rows if get_datetime(r.time) < window_end or get_datetime(r.creation) < window_end]
	employee_of_user = {
		e.user_id: e.name
		for e in frappe.get_all("Employee", filters={"user_id": ("is", "set")}, fields=["name", "user_id"])
	}
	runs = frappe.get_all("HRMS Sync Run", fields=["owner", "started_at", "finished_at"], limit_page_length=0)
	operator_users = {r.owner for r in runs} | {"Administrator"}
	run_windows = [(r.started_at, r.finished_at) for r in runs if r.started_at]

	classified = []
	for row in rows:
		verdict = classify_punch(row, run_windows, employee_of_user, operator_users)
		classified.append({**row, **verdict})
	if employee:
		classified = [r for r in classified if (r["true_employee"] or r["employee"]) == employee]
	overwritten = [r for r in classified if r["kind"] == OVERWRITTEN]

	names = [r["name"] for r in overwritten]
	requests_by_checkin = {
		r.checkin: {"log_type": r.log_type, "checkin_time": r.checkin_time}
		for r in (
			frappe.get_all(
				"Remote Checkin Request",
				filters={"checkin": ("in", names)},
				fields=["checkin", "log_type", "checkin_time"],
			)
			if names
			else []
		)
	}
	local_punches = {}
	for r in classified:
		if r["kind"] == LOCAL:
			local_punches.setdefault(r["employee"], []).append(r)
	already_recovered = {
		d[len(RECOVERED_PREFIX) :]
		for d in frappe.get_all(
			"Employee Checkin", filters={"device_id": ("like", RECOVERED_PREFIX + "%")}, pluck="device_id"
		)
	}
	tz_memo = {}

	def tz_of(emp):
		if emp not in tz_memo:
			tz_memo[emp] = get_attendance_timezone(emp)
		return tz_memo[emp]

	plan = plan_recovery(
		overwritten, requests_by_checkin, local_punches, already_recovered, tz_of, get_system_timezone()
	)
	attendance = _attendance_by_day(plan)
	logger.info(
		"[checkin_recovery] %s..%s: %d punches, %d overwritten, %d planned inserts",
		from_date,
		to_date,
		len(classified),
		len(overwritten),
		sum(1 for e in plan if e["action"] == "insert"),
	)
	return {"rows": classified, "plan": plan, "attendance": attendance}


def _attendance_by_day(plan: list) -> dict:
	"""(employee, date) -> the day's Attendance row, submitted first."""
	if not plan:
		return {}
	employees = sorted({e["employee"] for e in plan if e["employee"]})
	days = [getdate(e["time"]) for e in plan]
	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": ("in", employees),
			"attendance_date": ("between", [min(days), max(days)]),
			"docstatus": ("!=", 2),
		},
		fields=[
			"name",
			"employee",
			"attendance_date",
			"status",
			"working_hours",
			"in_time",
			"out_time",
			"auto_attendance",
			"synced_from_instance",
			"docstatus",
		],
		order_by="docstatus desc",
	)
	out = {}
	for r in rows:
		out.setdefault((r.employee, getdate(r.attendance_date)), r)
	return out


@frappe.whitelist()
def recover_overwritten_checkins(from_date, to_date, dry_run=1) -> dict:
	"""Insert one new unstamped punch per overwritten row. Dry run by default.

	System Manager only: this writes attendance evidence for other people. The
	existing rows are never edited or deleted; re-running is safe because a
	recovered punch is recognised by its device_id.
	"""
	frappe.only_for("System Manager")
	plan = collect(from_date, to_date)["plan"]
	inserts = [e for e in plan if e["action"] == "insert"]
	if cint(dry_run):
		logger.info("[checkin_recovery] dry run by %s: %d inserts", frappe.session.user, len(inserts))
		return {"dry_run": True, "inserts": len(inserts), "plan": plan}

	inserted = failed = 0
	for entry in inserts:
		frappe.db.savepoint("ckin_recover")
		try:
			_insert_recovered(entry)
			inserted += 1
		except Exception:
			frappe.db.rollback(save_point="ckin_recover")
			failed += 1
			frappe.log_error(title=f"Checkin recovery failed for {entry['source_name']}")
			logger.exception("[checkin_recovery] insert failed for %s", entry["source_name"])
	logger.info(
		"[checkin_recovery] applied by %s: inserted=%d failed=%d skipped=%d",
		frappe.session.user,
		inserted,
		failed,
		len(plan) - len(inserts),
	)
	return {
		"dry_run": False,
		"inserted": inserted,
		"failed": failed,
		"skipped": len(plan) - len(inserts),
		"plan": plan,
	}


def _insert_recovered(entry: dict) -> None:
	doc = frappe.new_doc("Employee Checkin")
	doc.update(
		{
			"employee": entry["employee"],
			"log_type": entry["log_type"],
			"time": entry["time"],
			"device_id": RECOVERED_PREFIX + entry["source_name"],
		}
	)
	doc.flags.ignore_permissions = True
	# validate() holds the geofence and the duplicate-time check. A recovered
	# punch carries no coordinates and must never be routed to an approver, and
	# the plan already refused anything that duplicates a local row.
	doc.flags.ignore_validate = True
	doc.insert()
	# Shift fields the hourly job filters on, stamped the way "Fetch Shifts" does.
	doc.fetch_shift()
	doc.flags.ignore_validate = True
	doc.save()
	doc.add_comment(
		"Comment",
		_("Recovered from {0}: that row was overwritten by a sync pull from {1}. Log type {2} ({3}).").format(
			entry["source_name"], entry["stamped_from"], entry["log_type"], entry["confidence"]
		),
	)
	logger.info(
		"[checkin_recovery] inserted %s for %s at %s %s (%s) from %s",
		doc.name,
		entry["employee"],
		entry["time"],
		entry["log_type"],
		entry["confidence"],
		entry["source_name"],
	)
