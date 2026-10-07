import frappe
from frappe import _
from frappe.utils import add_days, date_diff

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

from hrms.hr.doctype.shift_assignment.shift_assignment import ShiftAssignment
from hrms.hr.doctype.shift_assignment_tool.shift_assignment_tool import create_shift_assignment
from hrms.hr.doctype.shift_schedule.shift_schedule import get_or_insert_shift_schedule
from hrms.hr.utils import rostered_employees
from hrms.telemetry import capture
from hrms.utils.company_scope import (
	get_permitted_companies,
	resolve_single_company,
	scope_employee_filters,
)

#: IT-assigned role that lets a branch leader roster their own team from Nadi
#: (or Desk). The role alone is not authority — every write is additionally
#: fenced to the caller's direct reports and permitted companies below.
ROSTER_SUPERVISOR_ROLE = "Shift Supervisor"

logger = frappe.logger("hrms")


def _ensure_can_roster(employee: str) -> None:
	"""Write fence for every roster action. Mirrors the read fence
	(_may_read_employee) but for WRITES, and fails CLOSED:

	  · HR operators (company-fenced) may roster anyone in their companies.
	  · A Shift Supervisor may roster themselves and their OWN direct reports
	    (Reports To), in any company — never another leader's team
	    (hrms.hr.utils.rostered_employees; owner rulings 30 Sep 2026).
	  · Everyone else is denied.

	This is the security boundary that keeps a multi-company hub from letting
	one branch leader touch another company's roster. Unwired, an endpoint that
	only checks the doctype create permission would let any Shift Supervisor
	roster every employee they can read — the exact "serves everyone, not just
	HR" trap. Pinned by test_roster_fence.
	"""
	from hrms.hr.utils import sees_all_employee_data
	from hrms.overrides.company_scope import company_visible

	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} does not exist.").format(employee), frappe.DoesNotExistError)

	company = frappe.db.get_value("Employee", employee, "company")
	if sees_all_employee_data(frappe.session.user) and company_visible(company):
		return

	# A Shift Supervisor rosters themselves and whoever reports to them, in
	# any company (owner, 30 Sep 2026: "Reports To wins"). One list, shared
	# with the shift row scope, so the list and the save cannot disagree.
	if employee in rostered_employees(frappe.session.user):
		return

	frappe.logger("hrms").warning(
		"[roster] %s denied roster write on employee %s", frappe.session.user, employee
	)
	frappe.throw(_("You are not permitted to roster this employee."), frappe.PermissionError)


def _ensure_can_roster_employee(employee: str) -> None:
	"""Every roster write's gate: may this caller roster this employee?

	Used to be `has_permission("Employee", "read")` THEN `_ensure_can_roster`.
	The read check applies the caller's Company User Permission, so a Shift
	Supervisor locked to one company was refused their own report in another
	before the roster fence ran (30 Sep 2026, HR: "dia tak boleh assign shift
	untuk budak dia"). Owner: Reports To wins. The roster fence is the stricter
	question (HR in company, or the supervisor's own line), so it is asked
	first; the Employee read stays for everyone it does not admit.
	"""
	_ensure_can_roster(employee)
	if employee not in rostered_employees(frappe.session.user):
		frappe.has_permission("Employee", "read", employee, throw=True)


ALLOWED_EMPLOYEE_FILTERS = {
	"status",
	"company",
	"department",
	"branch",
	"designation",
	"employee_name",
}

ALLOWED_SHIFT_FILTERS = {
	"shift_type",
	"status",
	"shift_location",
}


def _validate_employee_filters(employee_filters: dict[str, str]) -> None:
	for key, value in (employee_filters or {}).items():
		if key not in ALLOWED_EMPLOYEE_FILTERS:
			frappe.throw(
				_("Invalid employee filter: {0}").format(frappe.bold(key)),
				frappe.PermissionError,
			)
		# Values arrive as JSON from the roster UI and are always plain
		# strings. Rejecting anything else keeps the caller from smuggling in
		# an operator form (["in", [...]]) — the shape company fencing itself
		# uses to widen a query across the caller's permitted companies.
		if value is not None and not isinstance(value, str):
			frappe.logger("hrms").warning(
				"[api] roster rejected non-scalar employee filter %s from %s",
				key,
				frappe.session.user,
			)
			frappe.throw(
				_("Invalid employee filter: {0}").format(frappe.bold(key)),
				frappe.PermissionError,
			)


def _apply_employee_where(query, Employee, employee_filters: dict):
	"""Add the (already company-scoped) employee filters to a query.

	Understands the `["in", [...]]` form that `scope_employee_filters` emits
	for a caller permitted to see several companies; everything else is a
	plain equality filter.
	"""
	for key, value in employee_filters.items():
		if isinstance(value, list | tuple) and len(value) == 2 and str(value[0]).lower() == "in":
			query = query.where(Employee[key].isin(list(value[1])))
		else:
			query = query.where(Employee[key] == value)
	return query


def _validate_shift_filters(shift_filters: dict[str, str]) -> None:
	for key in shift_filters:
		if key not in ALLOWED_SHIFT_FILTERS:
			frappe.throw(
				_("Invalid shift filter: {0}").format(frappe.bold(key)),
				frappe.PermissionError,
			)


@frappe.whitelist(methods=["GET", "POST"])
def get_default_company() -> str:
	"""Company the roster header should preselect.

	The user default is only trustworthy for a caller who isn't company-fenced.
	A fenced caller gets their single permitted company; a caller permitted to
	see several gets nothing preselected — silently picking one of 15 companies
	for a group HR user is how the wrong roster ends up on screen.
	"""
	permitted = get_permitted_companies()
	if permitted is None:
		return frappe.defaults.get_user_default("Company")

	company = resolve_single_company(permitted)
	if not company:
		frappe.logger("hrms").info(
			"[api] roster.get_default_company: %s is permitted %d companies — no preselection",
			frappe.session.user,
			len(permitted),
		)
	return company or ""


@frappe.whitelist(methods=["GET", "POST"])
def get_events(
	month_start: str, month_end: str, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> dict[str, list[dict]]:
	_validate_employee_filters(employee_filters)
	_validate_shift_filters(shift_filters)
	holidays = get_holidays(month_start, month_end, employee_filters)
	leaves = get_leaves(month_start, month_end, employee_filters)
	shifts = get_shifts(month_start, month_end, employee_filters, shift_filters)

	events = {}
	for event in [holidays, leaves, shifts]:
		for key, value in event.items():
			if key in events:
				events[key].extend(value)
			else:
				events[key] = value
	return events


@frappe.whitelist(methods=["GET", "POST"])
def get_schedule_from_assignment(shift_schedule_assignment: str):
	frappe.has_permission("Shift Schedule Assignment", "read", shift_schedule_assignment, throw=True)
	shift_schedule = frappe.db.get_value(
		"Shift Schedule Assignment", shift_schedule_assignment, "shift_schedule"
	)
	frequency = frappe.db.get_value("Shift Schedule", shift_schedule, "frequency")
	repeat_on_days = frappe.get_all("Assignment Rule Day", filters={"parent": shift_schedule}, pluck="day")
	return {"frequency": frequency, "repeat_on_days": repeat_on_days}


@frappe.whitelist(methods=["POST"])
def create_shift_schedule_assignment(
	employee: str,
	company: str,
	shift_type: str,
	status: str,
	start_date: str,
	end_date: str | None,
	repeat_on_days: list[str],
	frequency: str,
	shift_location: str | None = None,
	day_type: str | None = None,
) -> None:
	_ensure_can_roster_employee(employee)
	frappe.has_permission("Shift Schedule Assignment", "create", throw=True)
	shift_schedule = get_or_insert_shift_schedule(shift_type, frequency, repeat_on_days)
	shift_schedule_assignment = frappe.get_doc(
		{
			"doctype": "Shift Schedule Assignment",
			"shift_schedule": shift_schedule,
			"employee": employee,
			"company": company,
			"shift_status": status,
			"shift_location": shift_location,
			"day_type": _valid_day_type(day_type),
			"enabled": 0 if end_date else 1,
		}
	).insert()

	capture(
		"shift_schedule_assignment_created",
		{
			"frequency": frequency,
			"status": status,
			"has_end_date": bool(end_date),
			"repeat_on_days": len(repeat_on_days or []),
		},
	)

	if not end_date or date_diff(end_date, start_date) <= 90:
		return shift_schedule_assignment.create_shifts(start_date, end_date)

	frappe.enqueue(
		shift_schedule_assignment.create_shifts, timeout=4500, start_date=start_date, end_date=end_date
	)


@frappe.whitelist(methods=["POST"])
def delete_shift_schedule_assignment(shift_schedule_assignment: str) -> None:
	schedule = frappe.get_doc("Shift Schedule Assignment", shift_schedule_assignment)
	# The roster fence decides, as for every roster write: HR in company or the
	# supervisor's own line. Frappe's own cancel/delete check refused a Shift
	# Supervisor (Fahmie, 3 Oct 2026); the role holds neither by design.
	_ensure_can_roster_employee(schedule.employee)
	shifts = [
		frappe.get_doc("Shift Assignment", name)
		for name in frappe.get_all(
			"Shift Assignment", {"shift_schedule_assignment": shift_schedule_assignment}, pluck="name"
		)
	]
	for doc in shifts:  # check every shift before removing any
		_refuse_worked_range_for_supervisor(doc.employee, doc.start_date, doc.end_date)
	for doc in shifts:
		_remove_assignment(doc)
	frappe.delete_doc("Shift Schedule Assignment", shift_schedule_assignment, ignore_permissions=True)
	logger.info("[roster] %s deleted schedule %s", frappe.session.user, shift_schedule_assignment)


def _remove_assignment(doc) -> None:
	"""Cancel and delete one Shift Assignment after the roster fence admitted it."""
	_ensure_can_roster_employee(doc.employee)
	doc.flags.ignore_permissions = True
	if doc.docstatus == 1:
		doc.cancel()
	frappe.delete_doc("Shift Assignment", doc.name, ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def delete_shift_assignment(assignment: str) -> None:
	"""Desk Roster "Delete -> All Consecutive Shifts": the whole assignment.

	Was frappe.client set_value(docstatus=2) + delete from the browser, which
	asks Frappe for cancel and delete — a Shift Supervisor holds neither, so
	the roster refused them (3 Oct 2026). Same fence as every roster write.
	"""
	doc = frappe.get_doc("Shift Assignment", assignment)
	_ensure_can_roster_employee(doc.employee)
	_refuse_worked_range_for_supervisor(doc.employee, doc.start_date, doc.end_date)
	logger.info("[roster] %s deletes %s", frappe.session.user, assignment)
	_remove_assignment(doc)


@frappe.whitelist(methods=["POST"])
def update_shift_assignment(assignment: str, status: str, end_date: str | None = None) -> None:
	"""Desk Roster "Update": status and end date of the whole assignment.

	Was frappe.client set_value from the browser — Frappe's write check, with
	the company User Permission, refused a supervisor's report in another
	company. Only the two fields that may change after submit.
	"""
	doc = frappe.get_doc("Shift Assignment", assignment)
	_ensure_can_roster_employee(doc.employee)
	if status not in ("Active", "Inactive"):
		frappe.throw(_("Status must be Active or Inactive."))
	from frappe.utils import add_days, getdate

	if status == "Inactive" and doc.status != "Inactive":
		# the whole assignment stops counting
		_refuse_worked_range_for_supervisor(doc.employee, doc.start_date, doc.end_date)
	elif end_date and (not doc.end_date or getdate(end_date) < getdate(doc.end_date)):
		# the days cut off the end stop counting
		_refuse_worked_range_for_supervisor(doc.employee, add_days(end_date, 1), doc.end_date)
	doc.flags.ignore_permissions = True
	doc.status = status
	doc.end_date = end_date or None
	doc.save()
	logger.info("[roster] %s updated %s: %s until %s", frappe.session.user, assignment, status, end_date)


@frappe.whitelist(methods=["POST"])
def swap_shift(
	src_shift: str, src_date: str, tgt_employee: str, tgt_date: str, tgt_shift: str | None
) -> None:
	if src_shift == tgt_shift:
		frappe.throw(_("Source and target shifts cannot be the same"))

	src_shift_doc = frappe.get_doc("Shift Assignment", src_shift)
	_ensure_can_roster_employee(src_shift_doc.employee)
	src_shift_doc.check_permission("write")

	_ensure_can_roster_employee(tgt_employee)
	frappe.has_permission("Shift Assignment", "create", throw=True)

	if tgt_shift:
		tgt_shift_doc = frappe.get_doc("Shift Assignment", tgt_shift)
		_ensure_can_roster_employee(tgt_shift_doc.employee)
		tgt_shift_doc.check_permission("write")
		tgt_company = tgt_shift_doc.company
		break_shift(tgt_shift_doc, tgt_date)
	else:
		tgt_company = frappe.db.get_value("Employee", tgt_employee, "company")

	# All guards passed and the swap is proceeding — capture only successful attempts.
	capture("shift_swapped", {"mutual_swap": bool(tgt_shift)})

	break_shift(src_shift_doc, src_date)
	# a swap moves a shift between two days; it is not a Day Type word, so it
	# never wipes a Roster Day marker (the whitelisted insert_shift would)
	_insert_shift(
		tgt_employee,
		tgt_company,
		src_shift_doc.shift_type,
		tgt_date,
		tgt_date,
		src_shift_doc.status,
		src_shift_doc.shift_location,
	)

	if tgt_shift:
		_insert_shift(
			src_shift_doc.employee,
			src_shift_doc.company,
			tgt_shift_doc.shift_type,
			src_date,
			src_date,
			tgt_shift_doc.status,
			tgt_shift_doc.shift_location,
		)


@frappe.whitelist(methods=["POST"])
def break_shift(assignment: str | ShiftAssignment, date: str) -> None:
	if isinstance(assignment, str):
		assignment = frappe.get_doc("Shift Assignment", assignment)

	_ensure_can_roster_employee(assignment.employee)
	# The fence above admits HR (in company) and a supervisor's own line. Past
	# it, a break is a roster EDIT: Frappe would still refuse the cancel +
	# delete a first-day break needs, which neither HR User nor Shift
	# Supervisor holds (owner, 2 Oct 2026; HR: "asal aku takleh update?").
	if assignment.employee not in rostered_employees(frappe.session.user):
		assignment.check_permission("write")
	assignment.flags.ignore_permissions = True
	logger.info("[roster] %s breaks %s on %s", frappe.session.user, assignment.name, date)

	if assignment.end_date and date_diff(assignment.end_date, date) < 0:
		frappe.throw(_("Cannot break shift after end date"))
	if date_diff(assignment.start_date, date) > 0:
		frappe.throw(_("Cannot break shift before start date"))

	employee = assignment.employee
	company = assignment.company
	shift_type = assignment.shift_type
	status = assignment.status
	end_date = assignment.end_date
	shift_location = assignment.shift_location
	day_type = assignment.get("day_type") or "None"

	if date_diff(date, assignment.start_date) == 0:
		assignment.cancel()
		assignment.delete()
	else:
		assignment.end_date = add_days(date, -1)
		assignment.save()

	if not end_date or date_diff(end_date, date) > 0:
		create_shift_assignment(
			employee,
			company,
			shift_type,
			add_days(date, 1),
			end_date,
			status,
			shift_location,
			ignore_permissions=True,
			day_type=day_type,
		)


def _refuse_worked_day(employee: str, date: str) -> None:
	"""A day with punches or attendance keeps its shift (owner ruling a, 2 Oct
	2026): taking it away would leave the punches pointing at no shift."""
	worked = frappe.db.exists(
		"Attendance", {"employee": employee, "attendance_date": date, "docstatus": ["!=", 2]}
	) or frappe.db.exists("Employee Checkin", {"employee": employee, "time": ["between", [date, date]]})
	if worked:
		logger.info("[roster] %s refused change on worked day %s %s", frappe.session.user, employee, date)
		from hrms.hr.utils import sees_all_employee_data

		if sees_all_employee_data(frappe.session.user):
			# HR is who a supervisor is sent to; never tell HR to ask HR
			frappe.throw(
				_("This day already has punches or attendance, so its shift cannot be changed here.")
			)
		frappe.throw(_("This day already has punches or attendance. Ask HR to change it."))


def _refuse_worked_range_for_supervisor(employee: str, start, end) -> None:
	"""A supervisor may not take a shift away from days already worked (owner
	ruling a, 2 Oct 2026) — the whole-assignment Delete / Update included
	(review of bb6400b3a). HR keeps its power: Frappe's on_cancel still guards
	linked punches and attendance for everyone."""
	from frappe.utils import getdate

	from hrms.hr.utils import sees_all_employee_data
	from hrms.utils.timezone import employee_now

	if sees_all_employee_data(frappe.session.user):
		return
	end = getdate(end) if end else employee_now(employee).date()
	start = getdate(start)
	if end < start:
		return
	worked = frappe.db.exists(
		"Attendance",
		{"employee": employee, "attendance_date": ["between", [start, end]], "docstatus": ["!=", 2]},
	) or frappe.db.exists("Employee Checkin", {"employee": employee, "time": ["between", [start, end]]})
	if worked:
		logger.info(
			"[roster] %s refused range %s..%s for %s: worked", frappe.session.user, start, end, employee
		)
		frappe.throw(_("Some of these days already have punches or attendance. Ask HR to change them."))


@frappe.whitelist(methods=["POST"])
def remove_shift_day(assignment: str, date: str) -> None:
	"""Nadi Team roster "Remove": take one day out of an assignment."""
	doc = frappe.get_doc("Shift Assignment", assignment)
	_ensure_can_roster_employee(doc.employee)
	_refuse_worked_day(doc.employee, date)
	logger.info("[roster] %s removes %s on %s", frappe.session.user, doc.name, date)
	break_shift(doc, date)


@frappe.whitelist(methods=["POST"])
def change_shift_day(
	assignment: str,
	date: str,
	shift_type: str,
	shift_location: str | None = None,
	day_type: str | None = None,
) -> None:
	"""Roster "Change": one day moves to another shift type, location or Day Type."""
	doc = frappe.get_doc("Shift Assignment", assignment)
	employee, company, status = doc.employee, doc.company, doc.status
	sent_day_type = day_type
	day_type = day_type or doc.get("day_type") or "None"
	logger.info(
		"[roster] %s changes %s on %s to %s (%s)", frappe.session.user, doc.name, date, shift_type, day_type
	)
	remove_shift_day(doc.name, date)
	_insert_shift(employee, company, shift_type, date, date, status, shift_location, day_type=day_type)
	if sent_day_type:
		# the caller named a Day Type for this one day: the last word wins over a marker
		_clear_day_markers(employee, date, date)


def _assignments_and_worked_days(employee: str, start) -> tuple[list, list]:
	"""What a shift change from `start` has to look at, read ONCE for the change and for its
	preview so the two can never disagree: the person's live assignments from that date, and
	every day from it that already carries Attendance or punches (by clock time AND by the shift
	day a punch was stamped to: an early IN, a night shift)."""
	from frappe.utils import getdate

	assignments = frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active"},
		or_filters=[["end_date", ">=", start], ["end_date", "is", "not set"]],
		fields=["name", "shift_type", "start_date", "end_date", "day_type", "synced_from_instance"],
	)
	worked = {
		getdate(day)
		for day in frappe.get_all(
			"Attendance",
			filters={"employee": employee, "attendance_date": [">=", start], "docstatus": ["!=", 2]},
			pluck="attendance_date",
		)
	} | {
		getdate(moment)
		for moment in frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "time": [">=", f"{start} 00:00:00"]},
			pluck="time",
		)
	} | {
		# a punch the day before, stamped to a shift day on or after the date (an early IN, a
		# night shift): cancelling that assignment would leave it pointing at nothing
		getdate(day)
		for day in frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "shift_start": [">=", f"{start} 00:00:00"]},
			pluck="shift_start",
		)
	}
	return assignments, sorted(worked)

def _asked_shifts(shifts) -> list[tuple]:
	"""The request's shifts as [(shift_type, days or None)], or a plain refusal."""
	import json

	try:
		asked = json.loads(shifts) if isinstance(shifts, str) else shifts
	except ValueError:
		frappe.throw(_("Pick the new shift."))
	if not isinstance(asked, list) or not all(isinstance(row, dict) for row in asked):
		frappe.throw(_("Pick the new shift."))
	new_shifts = [(row.get("shift_type"), row.get("days") or None) for row in asked]
	for shift_type, _days in new_shifts:
		if not shift_type or not frappe.db.exists("Shift Type", shift_type):
			frappe.throw(_("Pick a shift that exists."))
	return new_shifts

@frappe.whitelist(methods=["POST"])
def preview_shift_change(employee: str, start_date: str, shifts: str | list) -> dict:
	"""What `change_shift_from` WOULD do, said before HR presses it. Writes nothing.

	Same fence, same reads and same rule as the change (design review, 5 Oct 2026: the dialog
	must name the one-day changes the date would drop, and refuse a worked day as soon as it is
	picked). A refusal is returned in `refused`, not raised, so the dialog can show it inline.
	"""
	from datetime import timedelta

	from frappe.utils import getdate

	from hrms.hr.utils import sees_all_employee_data
	from hrms.utils.shift_change import ShiftChangeRefused, plan_change, preview_removed

	_ensure_can_roster_employee(employee)
	if not sees_all_employee_data(frappe.session.user):
		frappe.throw(_("Only HR can change a person's shift from a date."), frappe.PermissionError)
	start = getdate(start_date)
	new_shifts = _asked_shifts(shifts)
	assignments, worked = _assignments_and_worked_days(employee, start)
	try:
		plan_change(assignments, start, new_shifts, worked)
	except ShiftChangeRefused as refused:
		return {"ends_on": None, "removed": [], "refused": str(refused)}
	return {
		"ends_on": str(start - timedelta(days=1)),
		"removed": [
			{key: (str(value) if hasattr(value, "isoformat") else value) for key, value in row.items()}
			for row in preview_removed(assignments, start)
		],
		"refused": None,
	}

@frappe.whitelist(methods=["POST"])
def change_shift_from(employee: str, start_date: str, shifts: str | list, shift_location: str | None = None) -> dict:
	"""HR changes a person's shift from a date: 9-6 to 10-7, or Mon-Thu 10-7 and Fri 10-4.

	Was impossible from the screen: cancelling the old assignment is refused once
	punches exist ("linked to Employee Checkin"), and a submitted assignment keeps
	no editable shift. The old one is ENDED the day before instead (end_date is
	editable after submit), so nothing with punches is cancelled and the past stays
	exactly as it was. A date that already has punches or attendance is refused.
	HR only (owner, 5 Oct 2026): a supervisor keeps the per-day roster actions.

	`shifts`: [{"shift_type": ..., "days": ["Monday", ...] or null for every day}].
	One transaction: any failure leaves the roster as it was.
	"""
	from frappe.utils import getdate

	from hrms.hr.utils import sees_all_employee_data
	from hrms.utils.shift_change import ShiftChangeRefused, plan_change

	_ensure_can_roster_employee(employee)
	if not sees_all_employee_data(frappe.session.user):
		frappe.throw(_("Only HR can change a person's shift from a date."), frappe.PermissionError)

	start = getdate(start_date)
	new_shifts = _asked_shifts(shifts)
	assignments, worked = _assignments_and_worked_days(employee, start)
	try:
		plan = plan_change(assignments, start, new_shifts, worked)
	except ShiftChangeRefused as refused:
		frappe.throw(str(refused))

	company = frappe.db.get_value("Employee", employee, "company")
	day_type = plan.day_type
	logger.info("[roster] %s changes %s from %s: %s", frappe.session.user, employee, start, new_shifts)

	for name, last_day in plan.end:
		doc = frappe.get_doc("Shift Assignment", name)
		doc.flags.ignore_permissions = True
		doc.end_date = last_day
		doc.save()
	for name in plan.remove:
		_remove_assignment(frappe.get_doc("Shift Assignment", name))
	# a repeating schedule would keep creating the old shift after the change. Mirrored ones
	# belong to the old ERP (single-writer; set_value skips the write-block) and are ignored by
	# process_auto_shift_creation anyway, so they are left alone.
	stopped = frappe.get_all(
		"Shift Schedule Assignment",
		{"employee": employee, "enabled": 1, "synced_from_instance": ["is", "not set"]},
		pluck="name",
	)
	for name in stopped:
		frappe.db.set_value("Shift Schedule Assignment", name, "enabled", 0)
	if stopped:
		logger.info("[roster] %s switched off repeating schedules %s for %s", frappe.session.user, stopped, employee)

	for shift_type, days in plan.create:
		if not days:
			create_shift_assignment(
				employee, company, shift_type, plan.start, None, "Active", shift_location,
				ignore_permissions=True, day_type=day_type,
			)
			continue
		schedule = get_or_insert_shift_schedule(shift_type, "Every Week", days)
		repeat = frappe.get_doc(
			{
				"doctype": "Shift Schedule Assignment",
				"shift_schedule": schedule,
				"employee": employee,
				"company": company,
				"shift_status": "Active",
				"shift_location": shift_location,
				"day_type": _valid_day_type(day_type),
				"enabled": 1,
				"create_shifts_after": plan.start,
			}
		)
		repeat.flags.ignore_permissions = True
		repeat.insert()
		repeat.create_shifts(str(plan.start), None)
	return {"ended": len(plan.end), "removed": len(plan.remove), "created": len(plan.create)}

@frappe.whitelist(methods=["POST"])
def insert_shift(
	employee: str,
	company: str,
	shift_type: str,
	start_date: str,
	end_date: str | None,
	status: str,
	shift_location: str | None = None,
	day_type: str | None = None,
) -> None:
	"""Assign a shift over a date range (Nadi "Assign", Desk roster).

	Last word wins (7 Oct 2026): a Roster Day marker inside the dates is the older
	word, so it goes in the same transaction. An open end clears every marker from
	the start on. Splits and swaps call `_insert_shift`, which keeps the markers.
	"""
	_insert_shift(employee, company, shift_type, start_date, end_date, status, shift_location, day_type)
	_clear_day_markers(employee, start_date, end_date or None)


def _insert_shift(
	employee: str,
	company: str,
	shift_type: str,
	start_date: str,
	end_date: str | None,
	status: str,
	shift_location: str | None = None,
	day_type: str | None = None,
) -> None:
	_ensure_can_roster_employee(employee)
	frappe.has_permission("Shift Assignment", "create", throw=True)
	day_type = _valid_day_type(day_type)
	# A supervisor's own line is admitted by the roster fence above, company
	# lock or not ("Reports To wins", 30 Sep 2026). Frappe's User Permission
	# layer would still refuse a report in another company, so for that line
	# the per-document checks are the fence's, not Frappe's.
	# ceiling: only insert_shift (Team roster "Assign") skips the lock; upgrade:
	# swap/break/schedule the same way when the Desk roster is used across
	# companies.
	own_line = employee in rostered_employees(frappe.session.user)
	if own_line:
		# The company comes from the employee, never the browser: with Frappe's
		# per-document checks skipped for this line, a caller-chosen company
		# would file the shift under a company the employee is not in
		# (review of 7913dc781).
		company = frappe.db.get_value("Employee", employee, "company")

	def may(ptype, name):
		if not own_line:
			frappe.has_permission("Shift Assignment", ptype, name, throw=True)

	filters = {
		"doctype": "Shift Assignment",
		"employee": employee,
		"company": company,
		"shift_type": shift_type,
		"status": status,
		"shift_location": shift_location,
		# a neighbour joins this one only when it is the same kind of day
		"day_type": day_type,
		"docstatus": ["!=", 2],
	}
	prev_shift = frappe.db.exists(dict({"end_date": add_days(start_date, -1)}, **filters))
	next_shift = (
		frappe.db.exists(dict({"start_date": add_days(end_date, 1)}, **filters)) if end_date else None
	)

	if prev_shift:
		may("write", prev_shift)
		if next_shift:
			may("write", next_shift)
			end_date = frappe.db.get_value("Shift Assignment", next_shift, "end_date")
			may("delete", next_shift)
			frappe.db.set_value("Shift Assignment", next_shift, "docstatus", 2)
			frappe.delete_doc("Shift Assignment", next_shift, ignore_permissions=own_line)
		frappe.db.set_value("Shift Assignment", prev_shift, "end_date", end_date or None)

	elif next_shift:
		may("write", next_shift)
		frappe.db.set_value("Shift Assignment", next_shift, "start_date", start_date)

	else:
		create_shift_assignment(
			employee,
			company,
			shift_type,
			start_date,
			end_date,
			status,
			shift_location,
			ignore_permissions=own_line,
			day_type=day_type,
		)


#: Longest stretch one set_day_type call marks (two pay windows' worth).
# ceiling: 62 days per call, upgrade: HR asks to mark a longer stretch in one go.
MAX_DAY_TYPE_DAYS = 62


@frappe.whitelist(methods=["POST"])
def set_day_type(
	employee: str, from_date: str, to_date: str | None = None, day_type: str | None = None
) -> dict:
	"""Mark days Off / Rest / Public Holiday / Work Day for a person with NO shift.

	HR (6 Oct 2026): "kalau aku letak off day macam tu je tak boleh save, kena ada
	shift". The marker is a "Roster Day" row (one per person per date); every pay
	and attendance reader asks `_classify_day`, which reads it before any Shift
	Assignment. An empty day_type (or "None") deletes the markers in the range.
	Same write fence as insert_shift; a day with punches or attendance is refused
	for everyone (HR may re-type a worked day in a later release).

	Idempotent: the same call twice leaves the same rows. Returns {"saved": n}:
	the days now carrying the word, or the markers removed when clearing.
	"""
	from datetime import timedelta

	from frappe.utils import getdate

	from hrms.utils.ot_calculation import ROSTER_DAY_TYPES, forget_rostered_day_types

	_ensure_can_roster_employee(employee)
	clearing = day_type in (None, "", "None")
	if not clearing and day_type not in ROSTER_DAY_TYPES:
		frappe.throw(_("Day Type must be one of {0}.").format(", ".join(ROSTER_DAY_TYPES)))
	if not from_date:
		frappe.throw(_("Pick the day."))
	start = getdate(from_date)
	end = getdate(to_date) if to_date else start
	if end < start:
		frappe.throw(_("The last day cannot be before the first day."))
	if (end - start).days + 1 > MAX_DAY_TYPE_DAYS:
		frappe.throw(_("Mark at most {0} days at a time.").format(MAX_DAY_TYPE_DAYS))
	if not frappe.db.table_exists("Roster Day"):
		# deploy skew: the code is new, the site not migrated yet
		frappe.throw(_("Day markers are not ready on this site yet. Ask IT to update it."))

	days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
	for day in days:
		_refuse_worked_day(employee, str(day))

	# The fence above admits HR (in company) and a supervisor's own line; for that
	# line Frappe's per-document checks are skipped, as insert_shift does.
	own_line = employee in rostered_employees(frappe.session.user)
	marked = {
		getdate(row.date): row
		for row in frappe.get_all(
			"Roster Day",
			filters={"employee": employee, "date": ["between", [str(start), str(end)]]},
			fields=["name", "date", "day_type"],
		)
	}
	saved = 0
	for day in days:
		row = marked.get(day)
		if clearing:
			if row:
				frappe.delete_doc("Roster Day", row.name, ignore_permissions=own_line)
				saved += 1
			continue
		if not row:
			doc = frappe.get_doc(
				{"doctype": "Roster Day", "employee": employee, "date": str(day), "day_type": day_type}
			)
			doc.flags.ignore_permissions = own_line
			doc.insert()
		elif row.day_type != day_type:
			doc = frappe.get_doc("Roster Day", row.name)
			doc.day_type = day_type
			doc.flags.ignore_permissions = own_line
			doc.save()
		saved += 1
	forget_rostered_day_types()
	logger.info(
		"[roster] %s set %s..%s of %s to %s: %d day(s)",
		frappe.session.user,
		start,
		end,
		employee,
		day_type or "cleared",
		saved,
	)
	return {"saved": saved}


def _clear_day_markers(employee: str, start_date, end_date=None) -> int:
	"""Delete the Roster Day markers of `employee` from start_date to end_date (an
	open end = every marker from start_date on): an assignment written over those
	dates is the newer word (last word wins, 7 Oct 2026). Only called after the
	roster fence admitted the caller for this employee."""
	if not frappe.db.table_exists("Roster Day"):
		return 0  # deploy skew: no table, no markers
	dates = ["between", [str(start_date), str(end_date)]] if end_date else [">=", str(start_date)]
	names = frappe.get_all("Roster Day", filters={"employee": employee, "date": dates}, pluck="name")
	own_line = employee in rostered_employees(frappe.session.user)
	for name in names:
		frappe.delete_doc("Roster Day", name, ignore_permissions=own_line)
	if names:
		from hrms.utils.ot_calculation import forget_rostered_day_types

		forget_rostered_day_types()
		logger.info(
			"[roster] %s cleared %d day marker(s) of %s from %s to %s",
			frappe.session.user,
			len(names),
			employee,
			start_date,
			end_date or "open end",
		)
	return len(names)


def _valid_day_type(day_type: str | None) -> str:
	"""The roster's Day Type, from the doctype's own options (never the browser's word)."""
	field = frappe.get_meta("Shift Assignment").get_field("day_type")
	if not field:
		# deploy skew: the code is new, the site not migrated yet
		return "None"
	options = (field.options or "").split("\n")
	value = day_type or "None"
	if value not in options:
		frappe.throw(_("Day Type must be one of {0}.").format(", ".join(options)))
	return value


def get_holidays(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	_validate_employee_filters(employee_filters)
	employee_filters = scope_employee_filters(employee_filters, endpoint="roster.get_holidays")
	holidays = {}
	holiday_lists = {}

	for employee in frappe.get_list("Employee", filters=employee_filters, pluck="name"):
		if not (
			holiday_list := get_holiday_list_for_employee(employee, raise_exception=False, as_on=month_end)
		):
			continue
		if holiday_list not in holiday_lists:
			holiday_lists[holiday_list] = frappe.get_all(
				"Holiday",
				filters={"parent": holiday_list, "holiday_date": ["between", [month_start, month_end]]},
				fields=["name as holiday", "holiday_date", "description", "weekly_off"],
			)
		holidays[employee] = holiday_lists[holiday_list].copy()

	return holidays


def get_leaves(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	_validate_employee_filters(employee_filters)
	employee_filters = scope_employee_filters(employee_filters, endpoint="roster.get_leaves")
	LeaveApplication = frappe.qb.DocType("Leave Application")
	Employee = frappe.qb.DocType("Employee")

	query = frappe.qb.get_query(
		"Leave Application",
		fields=[
			LeaveApplication.name.as_("leave"),
			LeaveApplication.employee,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		],
		filters={
			"docstatus": 1,
			"status": "Approved",
			"from_date": ("<=", month_end),
			"to_date": (">=", month_start),
		},
		ignore_permissions=False,
	)

	query = query.left_join(Employee).on(LeaveApplication.employee == Employee.name)

	query = _apply_employee_where(query, Employee, employee_filters)

	return group_by_employee(query.run(as_dict=True))


def get_shifts(
	month_start: str, month_end: str, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> dict[str, list[dict]]:
	_validate_employee_filters(employee_filters)
	_validate_shift_filters(shift_filters)
	employee_filters = scope_employee_filters(employee_filters, endpoint="roster.get_shifts")
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	Employee = frappe.qb.DocType("Employee")

	query = frappe.qb.get_query(
		"Shift Assignment",
		fields=[
			ShiftAssignment.name,
			ShiftAssignment.employee,
			ShiftAssignment.shift_type,
			ShiftAssignment.shift_location,
			ShiftAssignment.day_type,
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftAssignment.status,
			ShiftAssignment.shift_schedule_assignment,
		],
		filters={
			"docstatus": 1,
			"start_date": ("<=", month_end),
		},
		ignore_permissions=False,
	)

	# end_date is open-ended (None for shifts with no defined end) — must be
	# expressed as an OR, which the filters dict can't represent cleanly.
	query = query.where((ShiftAssignment.end_date >= month_start) | (ShiftAssignment.end_date.isnull()))

	query = (
		query.left_join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.select(ShiftType.start_time, ShiftType.end_time, ShiftType.color)
		.left_join(Employee)
		.on(ShiftAssignment.employee == Employee.name)
	)

	query = _apply_employee_where(query, Employee, employee_filters)

	for filter in shift_filters:
		query = query.where(ShiftAssignment[filter] == shift_filters[filter])

	return group_by_employee(query.run(as_dict=True))


def group_by_employee(events: list[dict]) -> dict[str, list[dict]]:
	grouped_events = {}
	for event in events:
		grouped_events.setdefault(event["employee"], []).append(
			{k: v for k, v in event.items() if k != "employee"}
		)
	return grouped_events
