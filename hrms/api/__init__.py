import logging

import frappe
from frappe import _
from frappe.model import get_permitted_fields
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import Order
from frappe.utils import add_days, cint, date_diff, flt, get_last_day, getdate, strip_html

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

from hrms.hr.utils import get_designated_approvers, is_hr_operator
from hrms.utils.identity import (
	denial_message,
	get_employee,
	get_employee_info,
	require_employee,
	resolve_employee_identity,
)

logger = logging.getLogger(__name__)

SUPPORTED_FIELD_TYPES = [
	"Link",
	"Select",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
	"Table",
	"Check",
	"Data",
	"Float",
	"Int",
	"Section Break",
	"Date",
	"Time",
	"Datetime",
	"Currency",
]


@frappe.whitelist()
def get_current_user_info() -> dict:
	current_user = frappe.session.user
	user = frappe.db.get_value(
		"User", current_user, ["name", "first_name", "full_name", "user_image"], as_dict=True
	)
	user["roles"] = frappe.get_roles(current_user)
	# The PWA renders its HR gates (issue board, SOP management) from this
	# flag rather than carrying its own copy of the role list — the server's
	# HR_ROLES rule is the one implementation (test_is_hr_single_source pins
	# both ends).
	user["is_hr"] = is_hr_operator(current_user)

	return user


@frappe.whitelist()
def get_current_employee_info() -> dict:
	# Returns None when the caller resolves to no Employee — the PWA router keys
	# its /hrms/invalid-employee redirect off exactly that, so the contract is
	# preserved. What changed is *how* the employee is found: one canonical rule
	# in hrms.utils.identity, which normalizes the login, refuses ambiguity
	# instead of silently picking a row, and establishes the User <-> Employee
	# link for SSO users whose Employee carries their company email.
	return get_employee_info()


@frappe.whitelist()
def get_employee_identity_status() -> dict:
	"""Why the caller was denied, for the invalid-employee page.

	Split out rather than folded into `get_current_employee_info` so the happy
	path keeps returning a bare employee dict (or None) exactly as before. Costs
	one extra request, and only on the failure page.
	"""
	identity = resolve_employee_identity()
	return {
		"reason": identity.reason,
		"message": denial_message(identity.reason),
		"user": frappe.session.user,
	}


#: Request doctypes an employee may withdraw their OWN still-draft record.
#: Whitelisting keeps withdraw_request from becoming a delete-any-document hole
#: (Employee Checkin is deliberately absent — a punch is not a withdrawable
#: request even though it is docstatus 0).
WITHDRAWABLE_REQUEST_DOCTYPES = frozenset(
	{
		"Attendance Request",
		"Leave Application",
		"Expense Claim",
		"Shift Request",
		"OT Request",
		"Replacement Leave Claim",
	}
)


@frappe.whitelist()
def withdraw_request(doctype: str, name: str) -> None:
	"""Delete the caller's OWN, still-DRAFT request.

	Employees have no `delete` permission on these doctypes by design, so a saved
	draft — already sitting in the approver's queue (for_approval selects
	docstatus 0) — could never be recalled by the person who filed it. A draft
	was never approved, so pulling it back leaves no audit gap. This method IS
	the authorization: the fence is explicit — a whitelisted request doctype,
	owned by the caller, still docstatus 0 — and only then is the delete run with
	ignore_permissions.
	"""
	if doctype not in WITHDRAWABLE_REQUEST_DOCTYPES:
		frappe.throw(_("{0} cannot be withdrawn.").format(_(doctype)))
	doc = frappe.get_doc(doctype, name)
	# A row mirrored from the source ERP is read-only on this hub during the
	# parallel run — the write-block on on_trash would refuse the delete anyway
	# (and the sync owns the row, so the owner check below would too). Refuse
	# here with a message that names the real fix instead of a generic denial.
	stamp = doc.get("synced_from_instance")
	if stamp:
		frappe.throw(
			_("This request is mirrored from {0} and can only be withdrawn on the source instance.").format(
				stamp
			)
		)
	if doc.owner != frappe.session.user:
		logger.warning(
			"[api] withdraw denied: %s is not the owner of %s %s", frappe.session.user, doctype, name
		)
		frappe.throw(_("You can only withdraw a request you filed."), frappe.PermissionError)
	if cint(doc.docstatus) != 0:
		frappe.throw(_("This request was already acted on and can no longer be withdrawn."))
	logger.info("[api] withdraw %s %s by %s", doctype, name, frappe.session.user)
	frappe.delete_doc(doctype, name, ignore_permissions=True)


# staff lockdown: non-HR callers get a minimal PDPA-safe directory
STAFF_DIRECTORY_FIELDS = ["name", "employee_name", "designation", "department", "image"]


@frappe.whitelist()
def get_all_employees() -> list[dict]:
	# is_hr_operator, not a hand-rolled intersection. One reachable delta from
	# the old `HR_ROLES & roles` body: Administrator now gets the HR field set
	# instead of the PDPA-minimal one — consistent with every other predicate,
	# where Administrator is exceptional framework authority.
	if is_hr_operator():
		fields = [
			"name",
			"employee_name",
			"designation",
			"department",
			"company",
			"reports_to",
			"user_id",
			"image",
			"status",
		]
		filters = {}
		# frappe.get_all bypasses the row-scope hooks, so the company fence has
		# to be restated: an "HR (Company)" user holds HR User/Manager and took
		# this branch, and without it the full directory — user_id included —
		# crossed their fence. The STAFF branch below stays group-wide on
		# purpose: it is the deliberately minimal PDPA-safe directory.
		from hrms.overrides.company_scope import allowed_companies

		fence = allowed_companies()
		if fence:
			filters["company"] = ("in", fence)
	else:
		frappe.logger("hrms").info("[api] minimal directory served to %s", frappe.session.user)
		fields = STAFF_DIRECTORY_FIELDS
		filters = {"status": "Active"}

	return frappe.get_all("Employee", fields=fields, filters=filters, limit=999999)


@frappe.whitelist()
def get_reports_to_employee_name(employee: str) -> str:
	caller = get_employee()
	reports_to = frappe.db.get_value("Employee", caller, "reports_to") if caller else None
	if not reports_to or reports_to != employee:
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	return frappe.db.get_value("Employee", employee, "employee_name") or ""


def get_current_employee() -> str:
	# Still a PermissionError when the caller has no active Employee — a User
	# created without an Employee mapping, or one whose Employee went Inactive —
	# but the message now says which of those it is instead of a bare
	# "Employee not found" that sent people to the wrong support queue.
	return require_employee()


# HR Settings
@frappe.whitelist()
def get_hr_settings() -> dict:
	"""Settings the PWA renders against, resolved for the SESSION EMPLOYEE.

	`allow_geolocation_tracking` is per COMPANY (a registered override in
	hrms.utils.company_settings), and this endpoint is the value CheckInPanel
	gates coordinate capture on. Served globally, a company with the override ON
	and the global OFF had the PWA capture no coordinates while the enforcing
	insert (CustomEmployeeCheckin.validate_distance_from_shift_location, itself
	per company) requires them — so enabling the per-entity rollout flag would
	have blocked that company's check-ins outright. The screen and the fence
	must resolve the flag the same way.

	The other two keys stay global: neither is company-overridable.
	"""
	from hrms.utils.company_settings import is_setting_enabled_for_employee

	settings = frappe.db.get_singles_dict("HR Settings", cast=True)
	return frappe._dict(
		allow_employee_checkin_from_mobile_app=settings.allow_employee_checkin_from_mobile_app,
		allow_geolocation_tracking=is_setting_enabled_for_employee(
			get_employee(), "allow_geolocation_tracking"
		),
		prevent_self_leave_approval=settings.prevent_self_leave_approval,
	)


# Notifications
@frappe.whitelist()
def get_unread_notifications_count() -> int:
	return frappe.db.count(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
	)


@frappe.whitelist()
def mark_all_notifications_as_read() -> None:
	frappe.db.set_value(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
		"read",
		1,
		update_modified=False,
	)


@frappe.whitelist()
def are_push_notifications_enabled() -> bool:
	try:
		return frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")
	except frappe.DoesNotExistError:
		# push notifications are not supported in the current framework version
		return False


# Attendance
def _ensure_own_employee_or_permitted(employee: str) -> None:
	"""Staff lockdown: staff may only query their own employee; a direct
	manager may read a report, and HR (subject to the company fence) may read
	inside their fence. Unknown ids are rejected explicitly.

	NOT `frappe.has_permission("Employee")`: the shipped Employee doctype
	grants the Employee role read at permlevel 0, and the company-fence hook
	fails open for a caller with no Company User Permission — which is the
	hub's normal SSO/mirror-provisioned account. So has_permission returned
	True for any employee id, and every per-employee endpoint below it leaked
	a colleague's data one enumerable id at a time. This resolves ownership by
	user_id and checks role/manager/fence explicitly, so it fails closed."""
	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} does not exist.").format(employee), frappe.DoesNotExistError)
	if _may_read_employee(employee):
		return
	frappe.logger("hrms").warning("[api] %s denied access to employee %s data", frappe.session.user, employee)
	frappe.throw(_("Not permitted to view this employee's data."), frappe.PermissionError)


def _may_read_employee(employee: str) -> bool:
	from hrms.overrides.company_scope import company_visible

	# Self and the direct-manager check both resolve the caller through the
	# canonical get_employee(), which normalizes the login (strip+lower). A raw
	# `user_id == session.user` compare would drift on a mirror-provisioned
	# Employee whose user_id was written case-unnormalized via db.set_value,
	# locking that user out of their own data — see hrms/utils/identity.py.
	caller_employee = get_employee()
	if caller_employee and employee == caller_employee:
		return True
	# A direct manager may read a report (read-only, resolved by the caller's
	# own Employee, never a caller-supplied id).
	if caller_employee and frappe.db.get_value("Employee", employee, "reports_to") == caller_employee:
		return True
	# HR operators (HR User / HR Manager, and Administrator), bounded by the
	# company fence: an unfenced operator sees all, a fenced one only inside
	# their companies. is_hr_operator deliberately excludes System Manager.
	if is_hr_operator() and company_visible(frappe.db.get_value("Employee", employee, "company")):
		return True
	return False


@frappe.whitelist()
def get_attendance_calendar_events(
	from_date: str, to_date: str, employee: str | None = None
) -> dict[str, str]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	holidays = get_holidays_for_calendar(employee, from_date, to_date)
	attendance = get_attendance_for_calendar(employee, from_date, to_date)
	events = {}

	date = getdate(from_date)
	while date_diff(to_date, date) >= 0:
		date_str = date.strftime("%Y-%m-%d")
		if date in attendance:
			events[date_str] = attendance[date]
		elif date in holidays:
			events[date_str] = "Holiday"
		date = add_days(date, 1)

	return events


def get_attendance_for_calendar(employee: str, from_date: str, to_date: str) -> list[dict[str, str]]:
	attendance = frappe.get_all(
		"Attendance",
		{"employee": employee, "attendance_date": ["between", [from_date, to_date]], "docstatus": 1},
		["attendance_date", "status"],
	)
	return {d["attendance_date"]: d["status"] for d in attendance}


def get_holidays_for_calendar(employee: str, from_date: str, to_date: str) -> list[str]:
	if holiday_list := get_holiday_list_for_employee(employee, raise_exception=False):
		return frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [from_date, to_date]]},
			pluck="holiday_date",
		)

	return []


@frappe.whitelist()
def get_shift_requests(
	employee: str | None = None,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
	history: bool = False,
) -> list[dict]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("Shift Request", employee, approver_id, for_approval, cint(history))
	fields = [
		"name",
		"employee",
		"employee_name",
		"shift_type",
		"from_date",
		"to_date",
		"status",
		"approver",
		"docstatus",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Shift Request"):
		fields.append(workflow_state_field)

	shift_requests = frappe.get_list(
		"Shift Request",
		fields=fields,
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in shift_requests:
			application["workflow_state_field"] = workflow_state_field

	return shift_requests


@frappe.whitelist()
def get_attendance_requests(
	employee: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("Attendance Request", employee, None, for_approval)
	fields = [
		"name",
		"reason",
		"employee",
		"employee_name",
		"from_date",
		"to_date",
		"include_holidays",
		"shift",
		# the Open/Approved/Rejected decision — without it the list could only
		# fall back to docstatus and showed every submitted request as "Submitted",
		# even an approved one.
		"status",
		"docstatus",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Attendance Request"):
		fields.append(workflow_state_field)

	attendance_requests = frappe.get_list(
		"Attendance Request",
		fields=fields,
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in attendance_requests:
			application["workflow_state_field"] = workflow_state_field

	return attendance_requests


@frappe.whitelist()
def get_ot_requests(
	employee: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	# Optional for the same reason as get_attendance_calendar_events above: the
	# PWA is session-scoped and fires this with `auto: true`, so `employee` is
	# whatever `employeeResource` has resolved to — and on a cold load that is
	# undefined. Required, the call raised TypeError before a line of the body
	# ran, and the panel rendered NOTHING: an errored resource has no `.data`
	# and the template is written `v-if="x.data"`.
	#
	# Silent by construction, which is why test_pwa_session_scope pins the SHAPE
	# rather than these two cases. Passing an employee explicitly still works and
	# is still permission-checked — that is how a team lead reads their reports.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("OT Request", employee, None, for_approval)
	logger.info("[api] ot requests employee=%s for_approval=%s", employee, for_approval)
	return frappe.get_list(
		"OT Request",
		fields=[
			"name",
			"employee",
			"employee_name",
			"ot_date",
			"shift",
			"punch_ot_hours",
			"claimed_hours",
			"compensation",
			"docstatus",
			"creation",
		],
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)


@frappe.whitelist()
def get_replacement_leave_claims(
	employee: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	# Optional for the same reason as get_attendance_calendar_events above: the
	# PWA is session-scoped and fires this with `auto: true`, so `employee` is
	# whatever `employeeResource` has resolved to — and on a cold load that is
	# undefined. Required, the call raised TypeError before a line of the body
	# ran, and the panel rendered NOTHING: an errored resource has no `.data`
	# and the template is written `v-if="x.data"`.
	#
	# Silent by construction, which is why test_pwa_session_scope pins the SHAPE
	# rather than these two cases. Passing an employee explicitly still works and
	# is still permission-checked — that is how a team lead reads their reports.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("Replacement Leave Claim", employee, None, for_approval)
	logger.info("[api] rl claims employee=%s for_approval=%s", employee, for_approval)
	return frappe.get_list(
		"Replacement Leave Claim",
		fields=[
			"name",
			"employee",
			"employee_name",
			"bank_month",
			"claimed_days",
			"hours_cost",
			"available_hours",
			"docstatus",
			"creation",
		],
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)


@frappe.whitelist()
def get_ot_claim_summary(employee: str, date: str) -> dict:
	"""Live form helper: what the punches prove for a day, and how this
	employee's approved OT is compensated."""
	from hrms.utils.ot_calculation import get_day_ot_breakdown

	_ensure_own_employee_or_permitted(employee)
	breakdown = get_day_ot_breakdown(employee, date)
	eligible = cint(frappe.db.get_value("Employee", employee, "eligible_for_overtime_pay"))
	shift = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": date, "docstatus": ("<", 2)},
		"shift",
	)
	return {
		"shift": shift,
		"punch_ot_hours": flt(breakdown["ot_hours"]),
		"eligible_for_overtime_pay": eligible,
		"compensation": "Overtime Pay" if eligible else "Replacement Leave",
	}


@frappe.whitelist()
def get_replacement_leave_bank_summary(employee: str) -> dict:
	"""The current month's convertible OT hours plus the requests feeding it,
	and the Replacement Leave allocation balance so the dashboard can show a
	card even before the first claim (an RL allocation only exists after one)."""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
	from hrms.hr.doctype.ot_request.ot_request import get_replacement_leave_bank
	from hrms.hr.doctype.replacement_leave_claim.replacement_leave_claim import (
		REPLACEMENT_LEAVE_TYPE,
	)

	_ensure_own_employee_or_permitted(employee)
	bank = get_replacement_leave_bank(employee)
	# Floor for display: the raw total can read negative once a spent credit ages
	# out of the window (the cancel guard needs that signal, the UI does not).
	bank["hours_available"] = max(0, cint(bank["hours_available"]))
	bank["balance_days"] = flt(get_leave_balance_on(employee, REPLACEMENT_LEAVE_TYPE, getdate()) or 0)
	logger.info(
		"[api] rl_bank_summary %s: balance %s days, bank %sh",
		employee,
		bank["balance_days"],
		bank["hours_available"],
	)
	bank["requests"] = (
		frappe.get_all(
			"OT Request",
			filters={
				"employee": employee,
				"compensation": "Replacement Leave",
				"docstatus": 1,
				"ot_date": ("between", [bank["period_start"], bank["period_end"]]),
			},
			fields=["name", "ot_date", "claimed_hours"],
			order_by="ot_date asc",
		)
		if bank["period_start"]
		else []
	)
	return bank


APPROVER_FIELD_MAP = {
	"Shift Request": "approver",
	"Leave Application": "leave_approver",
	"Expense Claim": "expense_approver",
}

# SCOPING INVARIANT (2026-08-19, pinned by test_approval_scoping_invariant):
# the system never GUESSES across a company boundary; a human may ASSIGN
# across one. These queues key on approver fields HR filled in by hand, so
# they carry NO company fence on purpose — the assignment IS the
# authorization, and a fence here would strand every deliberate cross-company
# assignment in a queue its owner can never see. The company-fenced path is
# the remote-checkin queue, whose approver an ALGORITHM picks. If HR ever
# wants same-company-only approvers, enforce it where the assignment is
# written, not here.


def get_filters(
	doctype: str,
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	history: bool = False,
) -> dict:
	filters = frappe._dict()
	if history:
		# decided requests where the current user was the approver — the
		# approval trail the Team tabs lose the moment a request is decided
		filters.docstatus = ("!=", 2)
		filters.employee = ("!=", employee)
		# Expense Claim keeps its decision in approval_status; status tracks payment
		status_field = "approval_status" if doctype == "Expense Claim" else "status"
		filters[status_field] = ("in", ["Approved", "Rejected"])
		if approver_id and doctype in APPROVER_FIELD_MAP:
			filters[APPROVER_FIELD_MAP[doctype]] = approver_id
		logger.info("[api] history filters %s approver=%s", doctype, approver_id)
	elif for_approval:
		filters.docstatus = 0
		filters.employee = ("!=", employee)

		if workflow := get_workflow(doctype):
			allowed_states = get_allowed_states_for_workflow(workflow, approver_id)
			filters[workflow.workflow_state_field] = ("in", allowed_states)
		elif doctype not in ("Attendance Request", "OT Request", "Replacement Leave Claim"):
			filters.status = "Open" if doctype == "Leave Application" else "Draft"
			if approver_id:
				filters[APPROVER_FIELD_MAP[doctype]] = approver_id
	else:
		filters.docstatus = ("!=", 2)
		filters.employee = employee

	return filters


@frappe.whitelist()
def get_shift_request_approvers(employee: str) -> str | list[str]:
	_ensure_own_employee_or_permitted(employee)
	shift_request_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["shift_request_approver", "department"],
	)

	department_approvers = []
	if department:
		# NO Department read demand here (upstream v16 added one; v15 never had
		# it). The own-employee fence above is the authorization, and this list
		# is exactly what the save-time fence reads permissionlessly — a
		# bare-Employee user must be able to see who they may route to.
		# Pinned by test_self_service_department_reads.
		department_approvers = get_department_approvers(department, "shift_request_approver")
		if not shift_request_approver:
			shift_request_approver = frappe.db.get_value(
				"Department Approver",
				{"parent": department, "parentfield": "shift_request_approver", "idx": 1},
				"approver",
			)

	shift_request_approver_name = frappe.db.get_value("User", shift_request_approver, "full_name", cache=True)

	if shift_request_approver and shift_request_approver not in [
		approver.name for approver in department_approvers
	]:
		department_approvers.insert(
			0, {"name": shift_request_approver, "full_name": shift_request_approver_name}
		)

	return department_approvers


@frappe.whitelist()
def get_shifts(employee: str | None = None) -> list[dict[str, str]]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	return (
		frappe.qb.from_(ShiftAssignment)
		.join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.select(
			ShiftAssignment.name,
			ShiftAssignment.shift_type,
			ShiftAssignment.shift_location,
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftType.start_time,
			ShiftType.end_time,
		)
		.where(
			(ShiftAssignment.employee == employee)
			& (ShiftAssignment.status == "Active")
			& (ShiftAssignment.docstatus == 1)
		)
		.orderby(ShiftAssignment.start_date, order=Order.asc)
	).run(as_dict=True)


# Leaves and Holidays
@frappe.whitelist()
def get_leave_applications(
	employee: str | None = None,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
	history: bool = False,
) -> list[dict]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("Leave Application", employee, approver_id, for_approval, cint(history))
	fields = [
		"name",
		"posting_date",
		"employee",
		"employee_name",
		"leave_type",
		"status",
		"from_date",
		"to_date",
		"half_day",
		"half_day_date",
		"description",
		"total_leave_days",
		"leave_balance",
		"leave_approver",
		"posting_date",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Leave Application"):
		fields.append(workflow_state_field)

	applications = frappe.get_list(
		"Leave Application",
		fields=fields,
		filters=filters,
		order_by="posting_date desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in applications:
			application["workflow_state_field"] = workflow_state_field

	return applications


@frappe.whitelist()
def get_leave_balance_map() -> dict[str, dict[str, float]]:
	"""
	Returns a map of leave type and balance details like:
	{
	        'Casual Leave': {
	                'allocated_leaves': 10.0,
	                'balance_leaves': 5.0,
	                'annual_entitlement': 14.0,
	                'carry_forwarded_leaves': 0.0,
	                'from_date': '2026-01-01',
	        },
	}

	annual_entitlement is the full-year entitlement used as the balance-card
	denominator, resolved in order:
	1. service-entitlement slab for the employee's grade and completed years of
	   service as of the allocation start — the same lookup the Leave Policy
	   Assignment ran at grant time (recomputed from current employee/slab
	   data, so it follows later grade/DOJ/slab corrections)
	2. annual_allocation of the Leave Policy assigned for the current period
	3. the allocated leaves themselves (manual/compensatory allocations)

	LWP leave types carry no meaningful balance and are excluded.
	"""
	from hrms.hr.doctype.leave_application.leave_application import (
		get_leave_allocation_records,
		get_leave_details,
	)
	from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
		get_leave_type_details,
	)
	from hrms.hr.doctype.leave_type.leave_type import get_service_based_leave_days

	# Resolve first, THEN guard. The endpoint became session-scoped (the PWA
	# calls it with no arguments) but the guard was left above the assignment,
	# so every call raised UnboundLocalError before reaching any of this.
	employee = get_current_employee()

	# Guards the policy/entitlement reads below, which bypass row-level
	# permissions (frappe.get_all), and rejects unknown employee ids cleanly.
	_ensure_own_employee_or_permitted(employee)

	date = getdate()
	leave_map = {}

	leave_details = get_leave_details(employee, date)
	allocation = leave_details["leave_allocation"]
	lwps = set(leave_details["lwps"])

	allocation_records = get_leave_allocation_records(employee, date)
	leave_types = get_leave_type_details()
	policy_allocations = get_policy_annual_allocations(employee, date)
	date_of_joining, grade = frappe.db.get_value("Employee", employee, ["date_of_joining", "grade"])
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

	for leave_type, details in allocation.items():
		if leave_type in lwps:
			continue

		record = allocation_records.get(leave_type, frappe._dict())
		allocated = flt(details.get("total_leaves"))

		entitlement = None
		if leave_types.get(leave_type, frappe._dict()).based_on_years_of_service:
			entitlement = get_service_based_leave_days(
				leave_type, date_of_joining, record.from_date or date, grade
			)
		if entitlement is None:
			entitlement = policy_allocations.get(leave_type)
		if not entitlement:
			# deliberately falsy, not `is None`: a 0 policy allocation must
			# never become the gauge denominator (n/0)
			entitlement = allocated

		leave_map[leave_type] = {
			"allocated_leaves": allocated,
			"balance_leaves": details.get("remaining_leaves"),
			"annual_entitlement": flt(entitlement, precision),
			"carry_forwarded_leaves": flt(record.get("unused_leaves"), precision),
			"from_date": record.get("from_date"),
		}

	frappe.logger("hrms").debug(
		"[api] Leave balance map for %s: %s",
		employee,
		{k: v["annual_entitlement"] for k, v in leave_map.items()},
	)
	return leave_map


def get_policy_annual_allocations(employee: str, date) -> dict[str, float]:
	"""annual_allocation per leave type from the employee's Leave Policy
	Assignment effective on `date` (empty when none is assigned)."""
	policy = frappe.db.get_value(
		"Leave Policy Assignment",
		{
			"employee": employee,
			"docstatus": 1,
			"effective_from": ("<=", date),
			"effective_to": (">=", date),
		},
		"leave_policy",
	)
	if not policy:
		frappe.logger("hrms").debug("[api] No Leave Policy Assignment covering %s for %s", date, employee)
		return {}

	details = frappe.get_all(
		"Leave Policy Detail",
		filters={"parenttype": "Leave Policy", "parent": policy},
		fields=["leave_type", "annual_allocation"],
	)
	return {d.leave_type: flt(d.annual_allocation) for d in details}


@frappe.whitelist()
def get_holidays_for_employee(employee: str) -> list[dict]:
	_ensure_own_employee_or_permitted(employee)
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return []

	# No doctype-level Holiday List check here, DELIBERATELY. The fence above is
	# the authorization ("may you ask about this employee"), and the list name is
	# resolved SERVER-SIDE from that employee — the caller never supplies it, so
	# there is nothing for a doctype read check to protect. The check that used
	# to sit here 403'd every hub-provisioned user: they carry the bare Employee
	# role (ensure_employee_role, by design), while Holiday List read ships only
	# inside the ESS user-type bundle this hub deliberately does not use — and
	# the SAME dates already flow to the SAME user through
	# get_holidays_for_calendar, which never asked. One rule for both readers;
	# do not re-add the check in a hardening pass without also deciding the ESS
	# provisioning question.
	Holiday = frappe.qb.DocType("Holiday")
	holidays = (
		frappe.qb.from_(Holiday)
		.select(Holiday.name, Holiday.holiday_date, Holiday.description)
		.where((Holiday.parent == holiday_list) & (Holiday.weekly_off == 0))
		.orderby(Holiday.holiday_date, order=Order.asc)
	).run(as_dict=True)

	for holiday in holidays:
		holiday["description"] = strip_html(holiday["description"] or "").strip()

	return holidays


@frappe.whitelist()
def get_leave_approval_details(employee: str) -> dict:
	_ensure_own_employee_or_permitted(employee)
	leave_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["leave_approver", "department"],
	)

	if not leave_approver and department:
		# No Department read demand — see get_shift_request_approvers; pinned
		# by test_self_service_department_reads.
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name", cache=True)
	# Options come from the same list validate_staff_approver enforces. Using
	# get_department_approvers here instead would offer the whole department
	# ANCESTOR chain, and picking one of those failed on save with "not one of
	# your designated approvers".
	department_approvers = _approver_options(employee, "leave_approver", "leave_approvers")

	return dict(
		leave_approver=leave_approver,
		leave_approver_name=leave_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value(
			"HR Settings", "leave_approver_mandatory_in_leave_application"
		),
	)


def _approver_options(employee: str, employee_approver_field: str, department_parentfield: str) -> list[dict]:
	"""Selector options, built from the list the backend fence actually accepts.

	The PWA renders these as the approver dropdown. Keeping it identical to
	`validate_staff_approver`'s allowed set is the whole point: a selector that
	offers more than the fence accepts produces a save-time rejection on a value
	the form itself suggested.
	"""
	approvers = get_designated_approvers(employee, employee_approver_field, department_parentfield)
	frappe.logger("hrms").debug("[api] %d approver option(s) for %s", len(approvers), employee)
	return [
		{"name": user, "full_name": frappe.db.get_value("User", user, "full_name", cache=True) or user}
		for user in approvers
	]


def get_department_approvers(department: str, parentfield: str) -> list[str]:
	if not department:
		return []

	department_details = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	departments = frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", department_details.lft),
			"rgt": (">=", department_details.rgt),
			"disabled": 0,
		},
		pluck="name",
	)

	Approver = frappe.qb.DocType("Department Approver")
	User = frappe.qb.DocType("User")
	department_approvers = (
		frappe.qb.from_(User)
		.join(Approver)
		.on(Approver.approver == User.name)
		.select(User.name.as_("name"), User.full_name.as_("full_name"))
		.where((Approver.parent.isin(departments)) & (Approver.parentfield == parentfield))
	).run(as_dict=True)

	return department_approvers


@frappe.whitelist()
def get_leave_types(employee: str, date: str) -> list:
	# Scope is enforced by get_leave_details' own guard, which — unlike
	# _ensure_own_employee_or_permitted — also admits the applicant's leave
	# approver. Approvers open this form for their team, and a 403 here blanks
	# the dropdown behind a "Could not load leave types" toast.
	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} does not exist.").format(employee), frappe.DoesNotExistError)
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = date or getdate()

	# Get leave details validate leave access internally
	leave_details = get_leave_details(employee, date)
	leave_types = list(leave_details["leave_allocation"].keys()) + leave_details["lwps"]

	# Drop types the employee is not eligible for yet. Leave Type.applicable_after
	# is enforced on save (validate_applicable_after); offering such a type in the
	# dropdown only to reject it after the applicant fills the whole form — the
	# "Prolonged Illness applicable after 183 days" trap — is offer-then-reject.
	# Mirror the save-time check exactly: eligible when days-since-joining meets
	# applicable_after (a from_date before joining is not checked there either).
	doj = frappe.db.get_value("Employee", employee, "date_of_joining")
	served = date_diff(getdate(date), doj) if doj else None

	def _applicable(leave_type: str) -> bool:
		after = cint(frappe.db.get_value("Leave Type", leave_type, "applicable_after"))
		return served is None or served < 0 or after <= 0 or served >= after

	return [lt for lt in leave_types if _applicable(lt)]


# Expense Claims
@frappe.whitelist()
def get_expense_claims(
	employee: str | None = None,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
	history: bool = False,
) -> list[dict]:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	filters = get_filters("Expense Claim", employee, approver_id, for_approval, cint(history))
	fields = [
		"`tabExpense Claim`.name",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.employee",
		"`tabExpense Claim`.employee_name",
		"`tabExpense Claim`.currency",
		"`tabExpense Claim`.approval_status",
		"`tabExpense Claim`.status",
		"`tabExpense Claim`.expense_approver",
		"`tabExpense Claim`.total_claimed_amount",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.company",
		"`tabExpense Claim`.creation",
		"`tabExpense Claim Detail`.expense_type",
		{"COUNT": "`tabExpense Claim Detail`.expense_type", "as": "total_expenses"},
	]

	if workflow_state_field := get_workflow_state_field("Expense Claim"):
		fields.append(workflow_state_field)

	claims = frappe.get_list(
		"Expense Claim",
		fields=fields,
		filters=filters,
		order_by="`tabExpense Claim`.posting_date desc",
		group_by="`tabExpense Claim`.name",
		limit=limit,
	)

	if workflow_state_field:
		for claim in claims:
			claim["workflow_state_field"] = workflow_state_field

	return claims


@frappe.whitelist()
def get_expense_claim_summary(employee: str | None = None) -> dict:
	# `employee` is optional because the PWA is session-scoped: it knows who is
	# signed in, not their Employee id. Required, this raised TypeError before a
	# line of the body ran, and the UI rendered a blank panel rather than an
	# error. Passing one explicitly still works and is still permission-checked —
	# that is how a manager reads their team.
	employee = employee or get_current_employee()
	_ensure_own_employee_or_permitted(employee)
	from frappe.query_builder.functions import Sum

	Claim = frappe.qb.DocType("Expense Claim")

	pending_claims_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Draft", Claim.total_claimed_amount).else_(0)
	)
	sum_pending_claims = Sum(pending_claims_case).as_("total_pending_amount")

	approved_claims_case = (
		frappe.qb.terms.Case()
		.when(Claim.approval_status == "Approved", Claim.total_sanctioned_amount)
		.else_(0)
	)
	sum_approved_claims = Sum(approved_claims_case).as_("total_approved_amount")

	approved_total_claimed_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Approved", Claim.total_claimed_amount).else_(0)
	)
	sum_approved_total_claimed = Sum(approved_total_claimed_case).as_("total_claimed_in_approved")

	rejected_claims_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Rejected", Claim.total_claimed_amount).else_(0)
	)
	sum_rejected_claims = Sum(rejected_claims_case).as_("total_rejected_amount")

	summary = (
		frappe.qb.from_(Claim)
		.select(
			sum_pending_claims,
			sum_approved_claims,
			sum_rejected_claims,
			sum_approved_total_claimed,
			Claim.company,
		)
		.where((Claim.docstatus != 2) & (Claim.employee == employee))
	).run(as_dict=True)[0]

	# The employee's OWN company, not the aggregate row's: with no GROUP BY,
	# summary.company is an arbitrary claim's company, so an employee holding
	# claims in two companies got a nondeterministic currency on the card.
	company = frappe.db.get_value("Employee", employee, "company")
	summary["company"] = company
	summary["currency"] = frappe.db.get_value("Company", company, "default_currency")

	return summary


@frappe.whitelist()
def get_expense_claim_types() -> list[dict]:
	ClaimType = frappe.qb.DocType("Expense Claim Type")

	return (frappe.qb.from_(ClaimType).select(ClaimType.name, ClaimType.description)).run(as_dict=True)


@frappe.whitelist()
def get_expense_approval_details(employee: str) -> dict:
	_ensure_own_employee_or_permitted(employee)
	expense_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["expense_approver", "department"],
	)

	if not expense_approver and department:
		# No Department read demand — see get_shift_request_approvers; pinned
		# by test_self_service_department_reads.
		expense_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "expense_approvers", "idx": 1},
			"approver",
		)

	expense_approver_name = frappe.db.get_value("User", expense_approver, "full_name", cache=True)
	# same source of truth as the backend fence — see get_leave_approval_details
	department_approvers = _approver_options(employee, "expense_approver", "expense_approvers")

	return dict(
		expense_approver=expense_approver,
		expense_approver_name=expense_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value("HR Settings", "expense_approver_mandatory_in_expense_claim"),
	)


# Employee Advance intentionally has no PWA endpoint: the doctype is
# read-only company-wide by policy (patches/v15_112_0) — staff may not
# request advances and the company does not issue them. The old
# get_employee_advance_balance reader had no caller anywhere and was
# removed with the dead ShiftAssignmentFormView route on 2026-08-19.


# Company
@frappe.whitelist()
def get_company_currencies() -> dict:
	Company = frappe.qb.DocType("Company")
	Currency = frappe.qb.DocType("Currency")

	query = (
		frappe.qb.from_(Company)
		.join(Currency)
		.on(Company.default_currency == Currency.name)
		.select(
			Company.name,
			Company.default_currency,
			Currency.name.as_("currency"),
			Currency.symbol.as_("symbol"),
		)
	)

	companies = query.run(as_dict=True)
	return {company.name: (company.default_currency, company.symbol) for company in companies}


@frappe.whitelist()
def get_currency_symbols() -> dict:
	Currency = frappe.qb.DocType("Currency")

	currencies = (frappe.qb.from_(Currency).select(Currency.name, Currency.symbol)).run(as_dict=True)

	return {currency.name: currency.symbol or currency.name for currency in currencies}


@frappe.whitelist()
def get_company_cost_center_and_expense_account(company: str) -> dict:
	# Own company answers without any Desk read. Upstream v16 added a Company
	# read demand here that v15 never had — the Department disease again: a
	# bare-Employee user prefilling THEIR OWN expense claim has no Company
	# read and got a toast instead of a form. Asking about a DIFFERENT
	# company still requires real Company read (Desk/HR callers). Pinned by
	# test_self_service_department_reads.
	own = get_employee_info(fields=("company",))
	if not (own and own.get("company") == company):
		frappe.has_permission("Company", "read", company, throw=True)
	return frappe.db.get_value(
		"Company", company, ["cost_center", "default_expense_claim_payable_account"], as_dict=True
	)


@frappe.whitelist()
def get_salary_currency(employee: str | None = None) -> str | None:
	"""The currency an expense claim should default to for `employee`.

	Exists so the expense form stops raw-reading Employee through
	frappe.client.get_value — the permission-fragile path a bare-Employee
	user cannot always take. Same fence as every self-service read: your own
	record always answers; someone else's requires real Employee read
	(approvers and HR reviewing a claim).
	"""
	employee = employee or get_employee()
	if not employee:
		return None
	_ensure_own_employee_or_permitted(employee)
	currency = frappe.db.get_value("Employee", employee, "salary_currency")
	logger.info("[api] salary_currency %s -> %s", employee, currency)
	return currency


# Form View APIs
@frappe.whitelist()
def get_doctype_fields(doctype: str) -> list[dict]:
	"""The fields this CALLER can actually fill in.

	A Link whose target the caller cannot read is a control that can only error.
	Reported with a console log: a normal employee opening New Expense Claim was
	shown Advances and Totals tabs holding Gain Loss Account, Bank / Cash
	Account, Payable Account, Project and Cost Center, and every picker threw

	    PermissionError: Insufficient Permission for <strong>Account</strong>

	the moment it was touched. Reproduced as a real Employee-role user:
	search_link("Account") and search_link("Currency") both raise, while
	search_link("Expense Claim Type") succeeds.

	This used to filter on fieldtype and `amended_from` alone and never asked
	who was looking — so the accounting half of a finance form was rendered to
	somebody with no accounting permissions and no way to complete it.

	Only LINK fields are filtered: any other type has no target to check, and
	dropping one for a permission that does not apply to it would blank the
	form.

	Optional links are safe to drop — accounts sets them later, and the employee
	could not fill them anyway. A REQUIRED link must never be dropped: it would
	move the failure from a visible picker to an unexplainable save. Expense
	Claim's `currency` is reqd=1 and is handled by
	`patches.v16_0.grant_employee_currency_read` instead.
	"""
	fields = frappe.get_meta(doctype).fields
	visible = []
	for field in fields:
		if field.fieldtype not in SUPPORTED_FIELD_TYPES or field.fieldname == "amended_from":
			continue
		if (
			field.fieldtype == "Link"
			and field.options
			and not field.reqd
			and not frappe.has_permission(field.options, "read")
		):
			logger.debug(
				"[api] %s.%s hidden — caller cannot read %s", doctype, field.fieldname, field.options
			)
			continue
		visible.append(field)
	return visible


@frappe.whitelist()
def get_doctype_states(doctype: str) -> dict:
	states = frappe.get_meta(doctype).states
	return {state.title: state.color.lower() for state in states}


# File
@frappe.whitelist()
def get_attachments(dt: str, dn: str):
	frappe.has_permission(dt, doc=dn, throw=True)
	return frappe.get_list(
		"File",
		fields=["name", "file_name", "file_url", "is_private"],
		filters={"attached_to_name": str(dn), "attached_to_doctype": dt},
	)


@frappe.whitelist()
def upload_base64_file(
	content: str, filename: str, dt: str | None = None, dn: str | None = None, fieldname: str | None = None
):
	import base64
	import io
	from mimetypes import guess_type

	from PIL import Image, ImageOps

	from frappe.handler import ALLOWED_MIMETYPES

	if dt and dn:
		frappe.has_permission(dt, ptype="write", doc=dn, throw=True)

	decoded_content = base64.b64decode(content)
	content_type = guess_type(filename)[0]
	if content_type not in ALLOWED_MIMETYPES:
		frappe.throw(_("You can only upload JPG, PNG, PDF, TXT or Microsoft documents."))

	if content_type.startswith("image/jpeg"):
		# transpose the image according to the orientation tag, and remove the orientation data
		with Image.open(io.BytesIO(decoded_content)) as image:
			transpose_img = ImageOps.exif_transpose(image)
			# convert the image back to bytes
			file_content = io.BytesIO()
			transpose_img.save(file_content, format="JPEG")
			file_content = file_content.getvalue()
	else:
		file_content = decoded_content

	frappe.has_permission(dt, "write", dn, throw=True)

	return frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": dt,
			"attached_to_name": dn,
			"attached_to_field": fieldname,
			"folder": "Home",
			"file_name": filename,
			"content": file_content,
			"is_private": 1,
		}
	).insert()


@frappe.whitelist()
def delete_attachment(filename: str):
	attached_to_doctype, attached_to_name, owner = frappe.db.get_value(
		"File", filename, ["attached_to_doctype", "attached_to_name", "owner"]
	)
	if attached_to_doctype and attached_to_name:
		frappe.has_permission(attached_to_doctype, "write", attached_to_name, throw=True)
	elif owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		# an UNattached file has no parent document to borrow a permission
		# check from — without this, any signed-in user could delete any
		# orphan File by name
		frappe.throw(_("You can only delete your own attachments."), frappe.PermissionError)
	frappe.delete_doc("File", filename)


@frappe.whitelist()
def _download_pdf(doctype: str, docname: str) -> str:
	import base64

	from frappe.utils.print_format import download_pdf

	default_print_format = frappe.get_meta(doctype).default_print_format or "Standard"

	try:
		download_pdf(doctype, docname, format=default_print_format)
	except Exception as e:
		frappe.throw(_("Failed to download PDF: {0}").format(str(e)))

	base64content = base64.b64encode(frappe.local.response.filecontent)
	content_type = frappe.local.response.type

	return f"data:{content_type};base64," + base64content.decode("utf-8")


# Workflow
@frappe.whitelist()
def get_workflow(doctype: str) -> dict:
	workflow = get_workflow_name(doctype)
	if not workflow:
		return frappe._dict()
	return frappe.get_doc("Workflow", workflow)


def get_workflow_state_field(doctype: str) -> str | None:
	workflow_name = get_workflow_name(doctype)
	if not workflow_name:
		return None

	override_status, workflow_state_field = frappe.db.get_value(
		"Workflow",
		workflow_name,
		["override_status", "workflow_state_field"],
	)
	# NOTE: checkbox labelled 'Don't Override Status' is named override_status hence the inverted logic
	if not override_status:
		return workflow_state_field
	return None


def get_allowed_states_for_workflow(workflow: dict, user_id: str) -> list[str]:
	user_roles = frappe.get_roles(user_id)
	return [transition.state for transition in workflow.transitions if transition.allowed in user_roles]


# Permissions
@frappe.whitelist()
def get_permitted_fields_for_write(doctype: str) -> list[str]:
	return get_permitted_fields(doctype, permission_type="write")
