"""Why does this employee's day read the way it does — and what would put it right.

7 September 2026, the second live day on Verifica: staff had punched IN and OUT
and the calendar still said Absent, Half Day or nothing, in every combination.
Each combination has ONE mechanical cause, and every cause is visible in the
rows themselves: a punch the hourly job never re-reads (skip-stamped by an
earlier Duplicate / Overlapping failure, linked to a cancelled row, under
another shift, before the shift's Process Attendance After, past its Last Sync
of Checkin, mirrored, rejected) or an attendance row the job never replaces
(manual, mirrored, leave, financially depended on). `judge_day` names the cause
for one employee-day from plain dicts, so it is testable without a bench and
readable by HR in the "Attendance Day Audit" report.

The repair does the two things the hourly job cannot do for itself and that
are pure lifecycle debris: clear a skip stamp the OLD failure handler wrote
(f8ca37e53 stopped writing it) and clear a link to a cancelled attendance.
Nothing else is written; the job then re-marks the day under the current rules
(fcb604535 / 2b01825d2 replace an automation-owned Absent or Half Day).
System Manager only, dry run by default.
"""

import logging

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate

logger = logging.getLogger(__name__)

# ceiling: judge_day is a 185-line if/elif returning 18 distinct verdicts, and
# repair_attendance_days one loop over 3 actions; upgrade: split each verdict
# into its own rule object BEFORE the next verdict or repair action is added —
# the count is already past what one function should carry.

#: Skip comments the OLD failure handler left that the repair may clear: the day
#: was blocked by another row, not by anything wrong with the punch.
REPAIRABLE_SKIP_REASONS = ("Duplicate", "Overlapping", "already exists")
#: A skip the job writes when payroll, approved overtime or replacement leave
#: already depends on the day (_repair_financial_dependency). Clearing it would
#: only make the next run write it back; HR corrects such a day by hand.
FINANCIAL_SKIP_MARKERS = ("depends on", "manual correction")
SKIP_PREFIX = "Reason for skipping auto attendance"


def _live(rows):
	return [r for r in rows if cint(r.get("docstatus")) < 2]


def judge_day(punches, attendance_rows, shift_config, skip_reasons=None, active_assignments=1) -> dict:
	"""One employee-day → {verdict, detail, repair}. Pure.

	`punches`: dicts with name, time, log_type, shift, attendance,
	skip_auto_attendance, offshift, remote_approval_status,
	synced_from_instance, shift_actual_end.
	`attendance_rows`: dicts with name, status, docstatus, auto_attendance,
	shift, leave_type, modify_half_day_status, synced_from_instance.
	`shift_config`: {name: {process_attendance_after, last_sync_of_checkin,
	enable_auto_attendance}} for the shifts the punches name.
	`skip_reasons`: {punch name: comment text}.
	`active_assignments`: how many Shift Assignments still cover this date for
	this employee. More than one is the usual cause of a split day; it is named
	in the detail so HR ends the superseded one, but the repair still runs,
	because re-resolving the day's punches in time order converges
	(hrms/utils/shift_resolution.py). Refusing it here once stranded exactly
	the employees whose days were broken.
	`repair` ∈ {"", "unskip", "unlink", "refetch-shift"}: what the repair would
	do to the punches.
	"""
	skip_reasons = skip_reasons or {}
	live = _live(attendance_rows)
	row = next((r for r in live if cint(r.get("docstatus")) == 1), live[0] if live else None)
	punches = sorted(punches, key=lambda p: get_datetime(p["time"]))

	if not punches and row is None:
		return _verdict("no-punches", "no punch and no attendance row", "")
	if row is not None:
		if row.get("synced_from_instance"):
			return _verdict(
				"row-mirrored", f"{row['name']} came from the source instance; the job never touches it", ""
			)
		if row.get("leave_type") or row.get("status") == "On Leave":
			return _verdict("row-leave", f"{row['name']} is a leave record", "")
		if not cint(row.get("auto_attendance")):
			return _verdict(
				"row-manual",
				f"{row['name']} was keyed by HR ({row.get('status')}); the job never touches it",
				"",
			)
		if cint(row.get("modify_half_day_status")):
			return _verdict("row-manual", f"{row['name']}: half-day status set by hand", "")

	linked = [p for p in punches if row is not None and p.get("attendance") == row["name"]]
	local = [p for p in punches if not p.get("synced_from_instance")]
	# what the job cannot or will not read
	skipped = [p for p in local if cint(p.get("skip_auto_attendance"))]
	reasons = {p["name"]: skip_reasons.get(p["name"], "") for p in skipped}
	if any(any(key in reason for key in FINANCIAL_SKIP_MARKERS) for reason in reasons.values()):
		return _verdict(
			"row-financially-locked",
			"payroll, approved overtime or replacement leave already depends on this day; HR corrects it by hand",
			"",
		)
	# Only a stamp the OLD failure handler wrote is debris. A rejection also
	# sets the flag and must stay: overtime eligibility reads it.
	repairable_skipped = [
		p
		for p in skipped
		if p.get("remote_approval_status") != "Rejected"
		and any(key in reasons[p["name"]] for key in REPAIRABLE_SKIP_REASONS)
	]
	if skipped and (repairable_skipped or len(skipped) == len(local)):
		return _verdict(
			"punches-skip-stamped",
			f"{len(skipped)} of {len(local)} punch(es) skip-stamped: "
			+ ("; ".join(sorted({r for r in reasons.values() if r})) or "no reason recorded"),
			"unskip" if repairable_skipped else "",
			[p["name"] for p in repairable_skipped],
		)
	# One day's punches under two shifts: the shift flip HR found on 10 Sep
	# (an OUT that jumped back to a superseded night shift). Each shift's job
	# then sees a single punch, so the day reads Half Day or Absent although
	# the row has a full IN and OUT. Re-resolving the shift and letting the
	# job rebuild the day is the repair.
	# Only punches the job would actually read can be repaired: a rejected or
	# skip-stamped punch is excluded from attendance by rule, and re-resolving
	# its shift buys nothing while muddying its audit trail.
	countable = [
		p
		for p in local
		if not cint(p.get("skip_auto_attendance"))
		and not cint(p.get("offshift"))
		and p.get("remote_approval_status") != "Rejected"
	]
	shifts_used = {p.get("shift") for p in countable if p.get("shift")}
	# Evidence of breakage, not merely two shifts: an employee legitimately
	# working two shifts in one day is not a defect, and "repairing" it would
	# re-resolve each punch back where it was, so the verdict would fire again
	# on every run. A day is broken when it has both an IN and an OUT and the
	# row still says Absent or Half Day (or there is no row at all).
	has_pair = {p.get("log_type") for p in countable} >= {"IN", "OUT"}
	looks_wrong = row is None or row.get("status") in ("Absent", "Half Day")
	if len(shifts_used) > 1 and has_pair and looks_wrong:
		# Repairable even while both assignments are still active: an OUT now
		# closes the shift its own IN opened (hrms/utils/shift_resolution.py),
		# so re-resolving the day's punches in time order converges on one
		# shift. Proven on a real site before this guard was relaxed. The
		# duplicate assignment is still named, because HR should end it.
		note = (
			f" ({active_assignments} shift assignments still cover this date — HR should end the superseded one)"
			if active_assignments > 1
			else ""
		)
		return _verdict(
			"punches-split-across-shifts",
			"the day's punches sit under "
			+ " and ".join(sorted(shifts_used))
			+ "; each shift saw only part of the day"
			+ note,
			"refetch-shift",
			[p["name"] for p in countable],
		)
	dead_link = [p for p in local if p.get("attendance") and (row is None or p["attendance"] != row["name"])]
	dead_link = [
		p
		for p in dead_link
		if not any(r["name"] == p["attendance"] and cint(r.get("docstatus")) < 2 for r in attendance_rows)
	]
	if dead_link:
		return _verdict(
			"punches-linked-to-cancelled-row",
			f"{len(dead_link)} punch(es) still point at a cancelled or missing attendance",
			"unlink",
			[p["name"] for p in dead_link],
		)
	mirrored = [p for p in punches if p.get("synced_from_instance")]
	if mirrored and len(mirrored) == len(punches):
		return _verdict(
			"punches-mirrored", "every punch is stamped as mirrored (see Checkin Provenance Audit)", ""
		)
	rejected = [p for p in punches if p.get("remote_approval_status") == "Rejected"]
	if rejected and len(rejected) == len(punches):
		return _verdict("punches-rejected", "every punch was rejected by the approver", "")
	if (
		row is not None
		and row.get("status") in ("Present", "Half Day", "Absent", "Work From Home")
		and punches
		and len(linked) == len(punches)
	):
		if row.get("status") == "Half Day" and len(linked) == 1:
			return _verdict(
				"half-day-one-punch",
				f"{row['name']}: Half Day from a single punch ({linked[0].get('log_type')})",
				"",
			)
		return _verdict("marked", f"{row['name']} {row.get('status')} from {len(linked)} punch(es)", "")

	unread = [p for p in punches if not p.get("attendance") and not cint(p.get("skip_auto_attendance"))]
	for p in unread:
		cfg = shift_config.get(p.get("shift") or "", {})
		if not p.get("shift"):
			return _verdict("punch-without-shift", f"{p['name']} resolved to no shift; no job reads it", "")
		if row is not None and row.get("shift") and p.get("shift") != row.get("shift"):
			return _verdict(
				"shift-mismatch", f"punch under {p['shift']}, attendance under {row['shift']}", ""
			)
		if not cint(cfg.get("enable_auto_attendance", 1)):
			return _verdict("shift-auto-attendance-off", f"{p['shift']}: Enable Auto Attendance is off", "")
		if cfg.get("process_attendance_after") and getdate(p["time"]) < getdate(
			cfg["process_attendance_after"]
		):
			return _verdict(
				"before-process-attendance-after",
				f"{p['shift']}: punch is before Process Attendance After ({cfg['process_attendance_after']})",
				"",
			)
		if (
			cfg.get("last_sync_of_checkin")
			and p.get("shift_actual_end")
			and get_datetime(p["shift_actual_end"]) >= get_datetime(cfg["last_sync_of_checkin"])
		):
			return _verdict(
				"after-last-sync",
				f"{p['shift']}: the job has not reached this shift yet (Last Sync of Checkin {cfg['last_sync_of_checkin']})",
				"",
			)
	if unread:
		what = f"{row['name']} {row.get('status')}" if row is not None else "no attendance row"
		return _verdict(
			"unread-punches",
			f"{len(unread)} unread punch(es) beside {what}: the next hourly run should mark the day — if it does not, read the Error Log",
			"",
		)
	return _verdict(
		"marked",
		f"{row['name']} {row.get('status')}" if row is not None else "punches linked, no live row",
		"",
	)


def _verdict(code, detail, repair, repair_punches=None):
	return {"verdict": code, "detail": detail, "repair": repair, "repair_punches": list(repair_punches or [])}


# --- frappe -------------------------------------------------------------------


def collect(from_date, to_date, employee=None) -> dict:
	"""Every employee-day in the window with punches or an attendance row, judged."""
	start, end = getdate(from_date), getdate(to_date)
	filters = {"time": ("between", [start, add_days(end, 1)])}
	if employee:
		filters["employee"] = employee
	punches = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"time",
			"log_type",
			"shift",
			"shift_start",
			"shift_actual_end",
			"attendance",
			"skip_auto_attendance",
			"offshift",
			"remote_approval_status",
			"synced_from_instance",
		],
		order_by="employee, time",
		limit_page_length=0,
	)
	att_filters = {"attendance_date": ("between", [start, end])}
	if employee:
		att_filters["employee"] = employee
	rows = frappe.get_all(
		"Attendance",
		filters=att_filters,
		fields=[
			"name",
			"employee",
			"employee_name",
			"attendance_date",
			"status",
			"docstatus",
			"auto_attendance",
			"shift",
			"leave_type",
			"modify_half_day_status",
			"synced_from_instance",
			"working_hours",
			"in_time",
			"out_time",
		],
		limit_page_length=0,
	)
	shift_names = {p.shift for p in punches if p.shift} | {r.shift for r in rows if r.shift}
	shift_config = (
		{
			s.name: s
			for s in frappe.get_all(
				"Shift Type",
				filters={"name": ("in", list(shift_names))},
				fields=["name", "process_attendance_after", "last_sync_of_checkin", "enable_auto_attendance"],
			)
		}
		if shift_names
		else {}
	)
	employees = {p.employee for p in punches} | {r.employee for r in rows}
	assignments = (
		frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": ("in", sorted(employees)),
				"docstatus": 1,
				"status": "Active",
				# Bounded to the window: without this the report pulls every
				# assignment an employee ever held, on a Desk report HR runs
				# over a month.
				"start_date": ("<=", end),
			},
			or_filters=[["end_date", ">=", start], ["end_date", "is", "not set"]],
			fields=["employee", "shift_type", "start_date", "end_date"],
			limit_page_length=0,
		)
		if employees
		else []
	)

	skipped_names = [p.name for p in punches if cint(p.skip_auto_attendance)]
	skip_reasons = {}
	if skipped_names:
		for c in frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Employee Checkin",
				"reference_name": ("in", skipped_names),
				"comment_type": "Comment",
			},
			fields=["reference_name", "content"],
			order_by="creation desc",
		):
			if SKIP_PREFIX in (c.content or "") and c.reference_name not in skip_reasons:
				skip_reasons[c.reference_name] = frappe.utils.strip_html(c.content)

	days = {}
	for p in punches:
		day = getdate(p.shift_start or p.time)
		days.setdefault((p.employee, day), {"punches": [], "rows": [], "employee_name": p.employee_name})
		days[(p.employee, day)]["punches"].append(p)
	for r in rows:
		days.setdefault(
			(r.employee, getdate(r.attendance_date)),
			{"punches": [], "rows": [], "employee_name": r.employee_name},
		)
		days[(r.employee, getdate(r.attendance_date))]["rows"].append(r)

	judged = []
	for (emp, day), bucket in sorted(days.items()):
		# The punch window runs one day past `end` to catch a post-midnight OUT
		# of the last day; a bucket dated outside the window has no attendance
		# rows fetched and would read as "linked to a missing row".
		if not (start <= day <= end):
			continue
		# Load-bearing with the window guard above: the assignment query is
		# bounded to [start, end], so a day outside that window would be counted
		# against an incomplete set and could read as one assignment when it has
		# two — i.e. falsely repairable.
		covering = sum(
			1
			for a in assignments
			if a.employee == emp
			and getdate(a.start_date) <= day
			and (not a.end_date or getdate(a.end_date) >= day)
		)
		verdict = judge_day(
			bucket["punches"], bucket["rows"], shift_config, skip_reasons, active_assignments=covering or 1
		)
		live = _live(bucket["rows"])
		row = next((r for r in live if cint(r.docstatus) == 1), live[0] if live else None)
		judged.append(
			{
				"employee": emp,
				"employee_name": bucket["employee_name"],
				"date": day,
				"punches": ", ".join(
					f"{get_datetime(p.time).strftime('%H:%M')} {p.log_type or ''}" for p in bucket["punches"]
				),
				"punch_count": len(bucket["punches"]),
				"attendance": row.name if row else None,
				"status": row.status if row else "",
				"working_hours": row.working_hours if row else None,
				"shift": row.shift if row else next((p.shift for p in bucket["punches"] if p.shift), None),
				**verdict,
			}
		)
	logger.info(
		"[attendance_day_audit] %s..%s employee=%s: %d days; %s",
		from_date,
		to_date,
		employee,
		len(judged),
		{v: sum(1 for j in judged if j["verdict"] == v) for v in {j["verdict"] for j in judged}},
	)
	return {"days": judged}


def plan_repairs(judged_days, locked_days=None) -> list:
	"""Which punches the repair would touch, and how. Pure.

	`locked_days` is the set of (employee, date) a payout already depends on.
	Re-shifting those is worse than leaving them: the rebuild is refused by the
	financial guard, and the job's own failure handler then skip-stamps every
	punch it just read — permanently, including the ones that were fine.
	"""
	locked = locked_days or set()
	plan = []
	for day in judged_days:
		if day.get("repair") == "refetch-shift" and (day["employee"], str(day["date"])) in locked:
			continue
		if day.get("repair") in ("unskip", "unlink", "refetch-shift") and day.get("repair_punches"):
			plan.append(
				{
					"employee": day["employee"],
					"date": str(day["date"]),
					"action": day["repair"],
					"punches": list(day.get("repair_punches") or []),
				}
			)
	return plan


def _job_can_read(punch) -> bool:
	"""Would the hourly job pick this punch up under the shift it now names?

	`ShiftType._process` skips a shift whose auto attendance is off, and its
	query takes punches with `time >= process_attendance_after` and
	`shift_actual_end < last_sync_of_checkin`. A punch outside that window is
	never read again, so unlinking it strands the day.
	"""
	if not punch.shift:
		return False
	shift = frappe.db.get_value(
		"Shift Type",
		punch.shift,
		["enable_auto_attendance", "process_attendance_after", "last_sync_of_checkin"],
		as_dict=True,
	)
	if not shift or not cint(shift.enable_auto_attendance):
		return False
	# ShiftType.has_incorrect_shift_config bails on either of these being unset,
	# so the job would never process that shift at all.
	if not (shift.process_attendance_after and shift.last_sync_of_checkin):
		return False
	if shift.process_attendance_after and getdate(punch.time) < getdate(shift.process_attendance_after):
		return False
	if (
		shift.last_sync_of_checkin
		and punch.shift_actual_end
		and get_datetime(punch.shift_actual_end) >= get_datetime(shift.last_sync_of_checkin)
	):
		return False
	return True


def _day_is_rewritable(punch_names) -> bool:
	"""Would EVERY punch of this day land on a shift the hourly job reads?

	Checked for the whole day before a single row is written. Half-applying a
	shift repair is worse than skipping it: if the IN's corrected shift is one
	the job never processes, the IN keeps its old shift, and the OUT then
	follows that old shift through the session rule — unifying the day onto the
	superseded shift instead of the right one.
	"""
	# In time order, carrying each resolved shift forward: a check-out inherits
	# the shift of the check-in it closes, so re-reading every punch from disk
	# would test the OUT against the IN's OLD shift and pass a day the repair
	# then half-applies.
	last_resolved = None
	for name in punch_names:
		punch = frappe.get_doc("Employee Checkin", name)
		stored = punch.shift
		punch.attendance = None
		if punch.log_type == "OUT" and last_resolved:
			punch.shift = last_resolved
		else:
			punch.fetch_shift()
			last_resolved = punch.shift
		if punch.shift != stored and not _job_can_read(punch):
			logger.info(
				"[attendance_day_audit] %s would land on %s, which the job never reads", name, punch.shift
			)
			return False
	return True


def _financially_locked(days, for_update: bool = True) -> set:
	"""(employee, date) where approved overtime, replacement leave or submitted
	payroll already depends on the day the shift repair would rebuild.

	`for_update` is False for the dry run: a preview must not hold Salary Slip
	locks and block payroll while somebody reads the screen.
	"""
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	locked = set()
	for day in days:
		if day.get("repair") != "refetch-shift":
			continue
		if _repair_financial_dependency(
			day["employee"], day["date"], day.get("attendance"), for_update=for_update
		):
			locked.add((day["employee"], str(day["date"])))
			logger.info(
				"[attendance_day_audit] %s on %s left alone: a payout depends on it",
				day["employee"],
				day["date"],
			)
	return locked


@frappe.whitelist()
def repair_attendance_days(from_date, to_date, dry_run=1, remark_now=0) -> dict:
	"""Clear old skip stamps and dead attendance links so the hourly job re-marks
	those days. System Manager only; dry run by default; writes nothing else."""
	frappe.only_for("System Manager")
	days = collect(from_date, to_date)["days"]
	locked = _financially_locked(days, for_update=not cint(dry_run))
	plan = plan_repairs(days, locked)
	if cint(dry_run):
		logger.info(
			"[attendance_day_audit] dry run by %s: %d day(s), %d held back for a payout",
			frappe.session.user,
			len(plan),
			len(locked),
		)
		return {"dry_run": True, "plan": plan, "held_back": sorted(locked)}

	touched = 0
	unchanged = 0
	for entry in plan:
		if entry["action"] == "refetch-shift" and not _day_is_rewritable(entry["punches"]):
			# Half-applying it is worse than not applying it: if the IN's
			# corrected shift is one the job can never read, the IN keeps its old
			# shift and the OUT then follows it, unifying the day onto the
			# superseded shift instead of the right one.
			logger.warning(
				"[attendance_day_audit] %s on %s left alone: a punch would land on a shift the job never reads",
				entry["employee"],
				entry["date"],
			)
			continue
		for name in entry["punches"]:
			if entry["action"] == "refetch-shift":
				# Through the document, on purpose: fetch_shift IS the rule
				# (hrms/utils/shift_resolution.py).
				punch = frappe.get_doc("Employee Checkin", name)
				was_linked = punch.attendance
				# The link must go FIRST: both fetch_shift implementations
				# assign the shift fields only `if not self.attendance`, so
				# re-resolving a still-linked punch computes and discards.
				was_shift = punch.shift
				punch.attendance = None
				punch.fetch_shift()
				if punch.shift == was_shift:
					unchanged += 1
					# Re-resolution agrees with what is already stored, so there
					# is nothing to correct. Saving would unlink the punch and
					# force a pointless rebuild — and, on a day that is split for
					# some other reason, would offer the same repair on every run.
					logger.info("[attendance_day_audit] %s already on %s, left as it is", name, was_shift)
					continue
				if not _job_can_read(punch):
					# Belt and braces: the whole day was checked above, so this
					# should not fire. If it ever does, nothing has been saved,
					# so the row on disk still holds its old shift and its link.
					logger.warning(
						"[attendance_day_audit] %s left alone: shift %s would never re-read it",
						name,
						punch.shift,
					)
					continue
				punch.flags.ignore_validate = True
				punch.save()
				logger.info(
					"[attendance_day_audit] %s re-resolved to %s (was linked to %s)",
					name,
					punch.shift,
					was_linked,
				)
			elif entry["action"] == "unskip":
				if not cint(frappe.db.get_value("Employee Checkin", name, "skip_auto_attendance")):
					continue
				frappe.db.set_value(
					"Employee Checkin", name, "skip_auto_attendance", 0, update_modified=False
				)
			else:
				frappe.db.set_value("Employee Checkin", name, "attendance", None, update_modified=False)
			frappe.get_doc("Employee Checkin", name).add_comment(
				"Comment",
				_("Attendance Day Audit repair by {0}: {1} — the hourly job re-marks this day.").format(
					frappe.session.user,
					_("skip stamp cleared")
					if entry["action"] == "unskip"
					else _("shift re-resolved")
					if entry["action"] == "refetch-shift"
					else _("link to a cancelled attendance cleared"),
				),
			)
			touched += 1
	if cint(remark_now) and touched:
		frappe.enqueue(
			"hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
			queue="long",
			timeout=3600,
		)
	logger.info(
		"[attendance_day_audit] applied by %s: %d punch(es) over %d day(s), remark_now=%s",
		frappe.session.user,
		touched,
		len(plan),
		remark_now,
	)
	logger.info("[attendance_day_audit] %d punch(es) rewritten, %d already correct", touched, unchanged)
	return {
		"dry_run": False,
		"touched": touched,
		"unchanged": unchanged,
		"days": len(plan),
		"plan": plan,
		"remark_queued": bool(cint(remark_now) and touched),
	}
