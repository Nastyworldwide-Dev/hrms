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
	insert_shift(
		tgt_employee,
		tgt_company,
		src_shift_doc.shift_type,
		tgt_date,
		tgt_date,
		src_shift_doc.status,
		src_shift_doc.shift_location,
	)

	if tgt_shift:
		insert_shift(
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
	day_type = day_type or doc.get("day_type") or "None"
	logger.info(
		"[roster] %s changes %s on %s to %s (%s)", frappe.session.user, doc.name, date, shift_type, day_type
	)
	remove_shift_day(doc.name, date)
	insert_shift(employee, company, shift_type, date, date, status, shift_location, day_type=day_type)


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
	import json

	from frappe.utils import getdate

	from hrms.hr.utils import sees_all_employee_data
	from hrms.utils.shift_change import ShiftChangeRefused, plan_change

	_ensure_can_roster_employee(employee)
	if not sees_all_employee_data(frappe.session.user):
		frappe.throw(_("Only HR can change a person's shift from a date."), frappe.PermissionError)

	start = getdate(start_date)
	asked = json.loads(shifts) if isinstance(shifts, str) else shifts
	new_shifts = [(row.get("shift_type"), row.get("days") or None) for row in asked or []]
	for shift_type, _days in new_shifts:
		if not shift_type or not frappe.db.exists("Shift Type", shift_type):
			frappe.throw(_("Pick a shift that exists."))

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
	}
	try:
		plan = plan_change(assignments, start, new_shifts, sorted(worked))
	except ShiftChangeRefused as refused:
		frappe.throw(str(refused))

	company = frappe.db.get_value("Employee", employee, "company")
	day_type = next((a.day_type for a in assignments if a.day_type and a.day_type != "None"), None)
	logger.info("[roster] %s changes %s from %s: %s", frappe.session.user, employee, start, new_shifts)

	for name, last_day in plan.end:
		doc = frappe.get_doc("Shift Assignment", name)
		doc.flags.ignore_permissions = True
		doc.end_date = last_day
		doc.save()
	for name in plan.remove:
		_remove_assignment(frappe.get_doc("Shift Assignment", name))
	# a repeating schedule would keep creating the old shift after the change
	for name in frappe.get_all(
		"Shift Schedule Assignment", {"employee": employee, "enabled": 1}, pluck="name"
	):
		frappe.db.set_value("Shift Schedule Assignment", name, "enabled", 0)

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
