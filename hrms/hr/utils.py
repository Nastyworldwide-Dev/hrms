# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import calendar
import datetime
import logging

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Count, Sum
from frappe.utils import (
	add_days,
	add_months,
	cint,
	comma_and,
	cstr,
	flt,
	format_datetime,
	formatdate,
	get_datetime,
	get_first_day,
	get_last_day,
	get_link_to_form,
	get_number_format_info,
	get_quarter_ending,
	get_quarter_start,
	get_year_ending,
	get_year_start,
	getdate,
	nowdate,
)

import erpnext
from erpnext import get_company_currency
from erpnext.setup.doctype.employee.employee import (
	InactiveEmployeeStatusError,
	get_holiday_list_for_employee,
)

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	calculate_pro_rated_leaves,
)

DateTimeLikeObject = str | datetime.date | datetime.datetime

logger = logging.getLogger(__name__)

# single source of truth for "who counts as HR" in staff-lockdown guards
HR_ROLES = frozenset({"HR User", "HR Manager", "System Manager"})

# See-all set for row scopes over CONFIDENTIAL employee data — team activity
# (leave, claims, shift/OT requests) and employee-owned records (pay, benefits,
# promotions, PIPs). System Manager is deliberately excluded: it is a technical
# role handed out for Desk administration, and holding it must not carry
# HR-wide sight of other people's requests or pay. Administrator is handled
# separately by each scope as exceptional framework authority.
#
# HR_ROLES is WRITE-side ONLY (filing for someone else,
# approver assignment), where System Manager acting as an operator is expected.
HR_SEE_ALL_ROLES = frozenset({"HR User", "HR Manager"})


def is_hr_operator(user: str | None = None) -> bool:
	"""Who may USE and SEE the HR-only surfaces: the issue board, SOPs, the
	full HR directory, 1-on-1 records, WPS files, and the PWA's `is_hr` flag.

	HR User / HR Manager only — NOT HR_ROLES. Policy ruling 2026-08-19:
	non-HR never sees HR-only surfaces, System Manager included. That
	deliberately departs from the v15 production behaviour (which showed the
	board to System Manager) and also cures v15's self-contradiction: SM
	"must not see pay" yet could pull WPS salary files. HR_ROLES — which
	keeps System Manager — now serves ONLY the write-side operator fences
	below (filing on behalf, approver assignment), where SM acts without
	seeing.

	Kept as its own name rather than folded into `sees_all_employee_data`:
	the two intents (operate HR content vs. see people's data) converged by
	ruling, and the seam stays so a future ruling can split them again
	without hunting call sites. Pinned by test_is_hr_single_source.
	"""
	return sees_all_employee_data(user)


def sees_all_employee_data(user: str | None = None) -> bool:
	"""The HR_SEE_ALL_ROLES rule as a predicate — sight over other people's
	confidential data (team browsing, leave/claims/shift approval scopes).
	System Manager is deliberately excluded; see the comment on the set.

	The ONE implementation, for the same reason as `is_hr_operator`: the
	line was previously duplicated in team.py and approval_row_scope.py.
	"""
	user = user or frappe.session.user
	return user == "Administrator" or bool(HR_SEE_ALL_ROLES & set(frappe.get_roles(user)))


class DuplicateDeclarationError(frappe.ValidationError):
	pass


class OverAllocationError(frappe.ValidationError):
	pass


def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")


def update_employee_work_history(employee, details, date=None, cancel=False):
	if not details:
		return employee

	if not employee.internal_work_history and not cancel:
		employee.append(
			"internal_work_history",
			{
				"branch": employee.branch,
				"designation": employee.designation,
				"department": employee.department,
				"from_date": employee.date_of_joining,
			},
		)

	internal_work_history = {}
	for item in details:
		field = frappe.get_meta("Employee").get_field(item.fieldname)
		if not field:
			continue

		new_value = item.new if not cancel else item.current
		new_value = get_formatted_value(new_value, field.fieldtype)
		setattr(employee, item.fieldname, new_value)

		if item.fieldname in ["department", "designation", "branch"]:
			internal_work_history[item.fieldname] = item.new

	if internal_work_history and not cancel:
		internal_work_history["from_date"] = date
		employee.append("internal_work_history", internal_work_history)

	if cancel:
		delete_employee_work_history(details, employee, date)

	update_to_date_in_work_history(employee, cancel)

	return employee


def get_formatted_value(value, fieldtype):
	"""
	Since the fields in Internal Work History table are `Data` fields
	format them as per relevant field types
	"""
	if not value:
		return

	if fieldtype == "Date":
		value = getdate(value)
	elif fieldtype == "Datetime":
		value = get_datetime(value)
	elif fieldtype in ["Currency", "Float"]:
		# in case of currency/float, the value might be in user's prefered number format
		# instead of machine readable format. Convert it into a machine readable format
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		decimal_str, comma_str, _number_format_precision = get_number_format_info(number_format)

		if comma_str == "." and decimal_str == ",":
			value = value.replace(",", "#$")
			value = value.replace(".", ",")
			value = value.replace("#$", ".")

		value = flt(value)

	return value


def delete_employee_work_history(details, employee, date):
	filters = {}
	for d in details:
		for history in employee.internal_work_history:
			if d.property == "Department" and history.department == d.new:
				department = d.new
				filters["department"] = department
			if d.property == "Designation" and history.designation == d.new:
				designation = d.new
				filters["designation"] = designation
			if d.property == "Branch" and history.branch == d.new:
				branch = d.new
				filters["branch"] = branch
			if date and date == history.from_date:
				filters["from_date"] = date
	if filters:
		frappe.db.delete("Employee Internal Work History", filters)
		employee.save()


def update_to_date_in_work_history(employee, cancel):
	if not employee.internal_work_history:
		return

	for idx, row in enumerate(employee.internal_work_history):
		if not row.from_date or idx == 0:
			continue

		prev_row = employee.internal_work_history[idx - 1]
		if not prev_row.to_date:
			prev_row.to_date = add_days(row.from_date, -1)

	if cancel:
		employee.internal_work_history[-1].to_date = None


@frappe.whitelist()
def get_employee_field_property(employee: str, fieldname: str):
	if not (employee and fieldname):
		return

	field = frappe.get_meta("Employee").get_field(fieldname)
	if not field:
		return

	doc = frappe.get_doc("Employee", employee, check_permission=True)
	value = doc.get(fieldname)

	if field.fieldtype == "Date":
		value = formatdate(value)
	elif field.fieldtype == "Datetime":
		value = format_datetime(value)

	return {
		"value": value,
		"datatype": field.fieldtype,
		"label": field.label,
		"options": field.options,
	}


def validate_dates(doc, from_date, to_date, restrict_future_dates=True):
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", doc.employee, ["date_of_joining", "relieving_date"]
	)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	elif getdate(from_date) > getdate(nowdate()) and restrict_future_dates:
		frappe.throw(_("Future dates not allowed"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))


def validate_overlap(doc, from_date, to_date, company=None):
	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New " + doc.doctype

	table = frappe.qb.DocType(doc.doctype)
	query = frappe.qb.from_(table).select(table.name).where(table.name != doc.name)

	condition = get_doc_condition(doc.doctype, table, doc.get("employee"), from_date, to_date, company)
	if condition is not None:
		query = query.where(condition)

	overlap_doc = query.run(as_dict=True)

	if overlap_doc:
		if doc.get("employee"):
			exists_for = doc.employee
		if company:
			exists_for = company
		throw_overlap_error(doc, exists_for, overlap_doc[0].name, from_date, to_date)


def get_doc_condition(doctype, table, employee, from_date, to_date, company):
	if doctype == "Compensatory Leave Request":
		return (
			(table.employee == employee)
			& (table.docstatus < 2)
			& (
				table.work_from_date.between(from_date, to_date)
				| table.work_end_date.between(from_date, to_date)
				| ((table.work_from_date < from_date) & (table.work_end_date > to_date))
			)
		)
	elif doctype == "Leave Period":
		return (table.company == company) & (
			table.from_date.between(from_date, to_date)
			| table.to_date.between(from_date, to_date)
			| ((table.from_date < from_date) & (table.to_date > to_date))
		)


def throw_overlap_error(doc, exists_for, overlap_doc, from_date, to_date):
	msg = (
		_("A {0} exists between {1} and {2} (").format(
			doc.doctype, formatdate(from_date), formatdate(to_date)
		)
		+ f""" <b><a href="/app/Form/{doc.doctype}/{overlap_doc}">{overlap_doc}</a></b>"""
		+ _(") for {0}").format(exists_for)
	)
	frappe.throw(msg)


def validate_duplicate_exemption_for_payroll_period(doctype, docname, payroll_period, employee):
	existing_record = frappe.db.exists(
		doctype,
		{
			"payroll_period": payroll_period,
			"employee": employee,
			"docstatus": ["<", 2],
			"name": ["!=", docname],
		},
	)
	if existing_record:
		frappe.throw(
			_("{0} already exists for employee {1} and period {2}").format(doctype, employee, payroll_period),
			DuplicateDeclarationError,
		)


def validate_tax_declaration(declarations):
	subcategories = []
	for d in declarations:
		if d.exemption_sub_category in subcategories:
			frappe.throw(_("More than one selection for {0} not allowed").format(d.exemption_sub_category))
		subcategories.append(d.exemption_sub_category)


def get_total_exemption_amount(declarations):
	exemptions = frappe._dict()
	for d in declarations:
		exemptions.setdefault(d.exemption_category, frappe._dict())
		category_max_amount = exemptions.get(d.exemption_category).max_amount
		if not category_max_amount:
			category_max_amount = frappe.db.get_value(
				"Employee Tax Exemption Category", d.exemption_category, "max_amount"
			)
			exemptions.get(d.exemption_category).max_amount = category_max_amount
		sub_category_exemption_amount = (
			d.max_amount if (d.max_amount and flt(d.amount) > flt(d.max_amount)) else d.amount
		)

		exemptions.get(d.exemption_category).setdefault("total_exemption_amount", 0.0)
		exemptions.get(d.exemption_category).total_exemption_amount += flt(sub_category_exemption_amount)

		if (
			category_max_amount
			and exemptions.get(d.exemption_category).total_exemption_amount > category_max_amount
		):
			exemptions.get(d.exemption_category).total_exemption_amount = category_max_amount

	total_exemption_amount = sum([flt(d.total_exemption_amount) for d in exemptions.values()])
	return total_exemption_amount


@frappe.whitelist()
def get_leave_period(from_date: str | datetime.date, to_date: str | datetime.date, company: str):
	LeavePeriod = frappe.qb.DocType("Leave Period")
	leave_period = (
		frappe.qb.from_(LeavePeriod)
		.select(LeavePeriod.name, LeavePeriod.from_date, LeavePeriod.to_date)
		.where(
			(LeavePeriod.company == company)
			& (LeavePeriod.is_active == 1)
			& (
				LeavePeriod.from_date[from_date:to_date]
				| LeavePeriod.to_date[from_date:to_date]
				| ((LeavePeriod.from_date < from_date) & (LeavePeriod.to_date > to_date))
			)
		)
	).run(as_dict=1)

	if leave_period:
		return leave_period


def generate_leave_encashment():
	"""Generates a draft leave encashment on allocation expiry"""
	from hrms.hr.doctype.leave_encashment.leave_encashment import create_leave_encashment

	if frappe.db.get_single_value("HR Settings", "auto_leave_encashment"):
		leave_type = frappe.get_all("Leave Type", filters={"allow_encashment": 1}, fields=["name"])
		leave_type = [l["name"] for l in leave_type]

		leave_allocation = frappe.get_all(
			"Leave Allocation",
			filters=[
				["to_date", "=", add_days(getdate(), -1)],
				["leave_type", "in", leave_type],
			],
			fields=[
				"employee",
				"leave_period",
				"leave_type",
				"to_date",
				"total_leaves_allocated",
				"new_leaves_allocated",
			],
		)

		create_leave_encashment(leave_allocation=leave_allocation)


def allocate_earned_leaves():
	"""Allocate earned leaves to Employees"""
	e_leave_types = get_earned_leaves()
	today = frappe.flags.current_date or getdate()
	failed_allocations = []
	for e_leave_type in e_leave_types:
		leave_allocations = get_leave_allocations(today, e_leave_type.name)
		for allocation in leave_allocations:
			if allocation.earned_leave_schedule_exists:
				allocation_date, earned_leaves = get_upcoming_earned_leave_from_schedule(
					allocation.name, today
				) or (None, None)
				annual_allocation = get_annual_allocation_from_policy(allocation, e_leave_type)
			else:
				date_of_joining = frappe.db.get_value("Employee", allocation.employee, "date_of_joining")
				allocation_date = get_expected_allocation_date_for_period(
					e_leave_type.earned_leave_frequency,
					e_leave_type.allocate_on_day,
					today,
					date_of_joining,
					effective_from=None,
				)
				annual_allocation = get_annual_allocation_from_policy(allocation, e_leave_type)
				earned_leaves = calculate_upcoming_earned_leave(allocation, e_leave_type, date_of_joining)

			if not allocation_date or allocation_date != today:
				continue
			try:
				update_previous_leave_allocation(
					allocation, annual_allocation, e_leave_type, earned_leaves, today
				)
			except Exception as e:
				log_allocation_error(allocation.name, e)
				failed_allocations.append(allocation.name)
	if failed_allocations:
		send_email_for_failed_allocations(failed_allocations)


def get_upcoming_earned_leave_from_schedule(allocation_name, today):
	return frappe.db.get_value(
		"Earned Leave Schedule",
		{"parent": allocation_name, "attempted": 0, "allocation_date": today},
		["allocation_date", "number_of_leaves"],
	)


def get_annual_allocation_from_policy(allocation, e_leave_type):
	return frappe.db.get_value(
		"Leave Policy Detail",
		filters={"parent": allocation.leave_policy, "leave_type": e_leave_type.name},
		fieldname=["annual_allocation"],
	)


def calculate_upcoming_earned_leave(allocation, e_leave_type, date_of_joining):
	annual_allocation = get_annual_allocation_from_policy(allocation, e_leave_type)
	earned_leave = get_monthly_earned_leave(
		date_of_joining,
		annual_allocation,
		e_leave_type.earned_leave_frequency,
		e_leave_type.rounding,
	)
	return earned_leave


def update_previous_leave_allocation(allocation, annual_allocation, e_leave_type, earned_leaves, today):
	allocation = frappe.get_doc("Leave Allocation", allocation.name)
	precision = allocation.precision("total_leaves_allocated")
	annual_allocation = flt(annual_allocation, precision)
	earned_leaves = flt(earned_leaves, precision)
	new_leaves_to_allocate_without_cf = flt(
		flt(allocation.get_existing_leave_count()) + earned_leaves,
		precision,
	)
	if (
		# annual allocation as per policy should not be exceeded except for yearly leaves
		new_leaves_to_allocate_without_cf > annual_allocation
		and e_leave_type.earned_leave_frequency != "Yearly"
	):
		frappe.throw(
			_("Allocation was skipped due to exceeding annual allocation set in leave policy"),
			OverAllocationError,
		)

	if e_leave_type.max_leaves_allowed:
		leaves_quota = flt(e_leave_type.max_leaves_allowed - allocation.total_leaves_allocated, precision)
		if leaves_quota <= 0:
			frappe.throw(
				_(
					"Allocation was skipped due to maximum leave allocation limit set in leave type. Please increase the limit and retry failed allocation."
				),
				OverAllocationError,
			)
		else:
			if leaves_quota < earned_leaves:
				earned_leaves = leaves_quota

	allocation.db_set(
		"total_leaves_allocated",
		earned_leaves + allocation.total_leaves_allocated,
		update_modified=False,
	)
	create_additional_leave_ledger_entry(allocation, earned_leaves, today)
	earned_leave_schedule = qb.DocType("Earned Leave Schedule")
	qb.update(earned_leave_schedule).where(
		(earned_leave_schedule.parent == allocation.name) & (earned_leave_schedule.allocation_date == today)
	).set(earned_leave_schedule.is_allocated, 1).set(earned_leave_schedule.attempted, 1).set(
		earned_leave_schedule.allocated_via, "Scheduler"
	).set(earned_leave_schedule.number_of_leaves, earned_leaves).run()


def log_allocation_error(allocation_name, error):
	error_log = frappe.log_error(error, reference_doctype="Leave Allocation")
	text = _("{0}. Check error log for more details.").format(error_log.method)
	earned_leave_schedule = qb.DocType("Earned Leave Schedule")
	today = getdate(frappe.flags.current_date) or getdate()

	qb.update(earned_leave_schedule).where(
		(earned_leave_schedule.parent == allocation_name) & (earned_leave_schedule.allocation_date == today)
	).set(earned_leave_schedule.attempted, 1).set(earned_leave_schedule.failed, 1).set(
		earned_leave_schedule.failure_reason, text
	).run()


def send_email_for_failed_allocations(failed_allocations):
	allocations = comma_and([get_link_to_form("Leave Allocation", x) for x in failed_allocations])
	User = frappe.qb.DocType("User")
	HasRole = frappe.qb.DocType("Has Role")
	query = (
		frappe.qb.from_(HasRole)
		.left_join(User)
		.on(HasRole.parent == User.name)
		.select(HasRole.parent)
		.distinct()
		.where((HasRole.parenttype == "User") & (User.enabled == 1) & (HasRole.role == "HR Manager"))
	)
	hr_managers = query.run(pluck=True)

	frappe.sendmail(
		recipients=hr_managers,
		subject=_("Failure of Automatic Allocation of Earned Leaves"),
		message=_(
			"Automatic Leave Allocation has failed for the following Earned Leaves: {0}. Please check {1} for more details."
		).format(allocations, get_link_to_form("Error Log", label="Error Log List")),
	)


@frappe.whitelist()
def get_monthly_earned_leave(
	date_of_joining: str | datetime.date,
	annual_leaves: float,
	frequency: str,
	rounding: str | float,
	period_start_date: str | datetime.date | None = None,
	period_end_date: str | datetime.date | None = None,
	pro_rated: bool = True,
):
	earned_leaves = 0.0
	divide_by_frequency = {"Yearly": 1, "Half-Yearly": 2, "Quarterly": 4, "Monthly": 12}
	if annual_leaves:
		earned_leaves = flt(annual_leaves) / divide_by_frequency[frequency]

		if pro_rated:
			if not (period_start_date or period_end_date):
				today_date = frappe.flags.current_date or getdate()
				period_start_date, period_end_date = get_sub_period_start_and_end(today_date, frequency)

			earned_leaves = calculate_pro_rated_leaves(
				earned_leaves, date_of_joining, period_start_date, period_end_date, is_earned_leave=True
			)

		earned_leaves = round_earned_leaves(earned_leaves, rounding)

	return earned_leaves


def get_sub_period_start_and_end(date, frequency, effective_from=None):
	if frequency == "Half-Yearly" and effective_from:
		return get_half_year_periods(date, effective_from)

	return {
		"Monthly": (get_first_day(date), get_last_day(date)),
		"Quarterly": (get_quarter_start(date), get_quarter_ending(date)),
		"Half-Yearly": (get_semester_start(date), get_semester_end(date)),  # fallback only
		"Yearly": (get_year_start(date), get_year_ending(date)),
	}.get(frequency)


def round_earned_leaves(earned_leaves, rounding):
	if not rounding:
		return earned_leaves

	if rounding == "0.25":
		earned_leaves = round(earned_leaves * 4) / 4
	elif rounding == "0.5":
		earned_leaves = round(earned_leaves * 2) / 2
	else:
		earned_leaves = round(earned_leaves)

	return earned_leaves


def get_leave_allocations(date, leave_type):
	employee = frappe.qb.DocType("Employee")
	leave_allocation = frappe.qb.DocType("Leave Allocation")
	earned_leave_schedule = frappe.qb.DocType("Earned Leave Schedule")

	query = (
		frappe.qb.from_(leave_allocation)
		.join(employee)
		.on(leave_allocation.employee == employee.name)
		.left_join(earned_leave_schedule)
		.on(leave_allocation.name == earned_leave_schedule.parent)
		.select(
			leave_allocation.name,
			leave_allocation.employee,
			leave_allocation.from_date,
			leave_allocation.to_date,
			leave_allocation.leave_policy_assignment,
			leave_allocation.leave_policy,
			Count(earned_leave_schedule.parent).as_("earned_leave_schedule_exists"),
		)
		.where(
			(date >= leave_allocation.from_date)
			& (date <= leave_allocation.to_date)
			& (leave_allocation.docstatus == 1)
			& (leave_allocation.leave_type == leave_type)
			& (leave_allocation.leave_policy_assignment.isnotnull())
			& (leave_allocation.leave_policy.isnotnull())
			& (employee.status != "Left")
			# Mirrored allocations are owned by their source instance
			# (single-writer, hrms/sync/write_block.py). Accrual writes the
			# ledger hook-free, so it must be excluded here at the query or the
			# balance double-counts against the source's own accrual.
			& (leave_allocation.synced_from_instance.isnull())
		)
		.groupby(leave_allocation.name)
	)
	return query.run(as_dict=1) or []


def get_earned_leaves():
	return frappe.get_all(
		"Leave Type",
		fields=[
			"name",
			"max_leaves_allowed",
			"earned_leave_frequency",
			"rounding",
			"allocate_on_day",
		],
		filters={"is_earned_leave": 1},
	)


def create_additional_leave_ledger_entry(allocation, leaves, date):
	"""Create leave ledger entry for leave types"""
	allocation.new_leaves_allocated = leaves
	allocation.from_date = date
	allocation.unused_leaves = 0
	allocation.create_leave_ledger_entry()


def _existing_rl_allocation(employee, leave_type, valid_from):
	"""The employee's submitted Replacement Leave allocation covering `valid_from`, or None."""
	logger.debug("[rl_grant] existing allocation lookup %s %s %s", employee, leave_type, valid_from)
	rows = frappe.db.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"leave_type": leave_type,
			"from_date": ("<=", valid_from),
			"to_date": (">=", valid_from),
			"docstatus": 1,
		},
		limit=1,
	)
	return frappe.get_doc("Leave Allocation", rows[0].name) if rows else None


def grant_replacement_leave(employee, employee_name, company, days, valid_from, description=None):
	"""Top up — or create — the employee's Replacement Leave allocation by `days`, with
	the ledger entry, and return the allocation name. This is the per-working-day grant
	the OT Request makes on approval (4h=½, 8h=1, 12h=1.5); the caller owns eligibility
	and the day count. Mirrors CompensatoryLeaveRequest.on_submit — top-up or create."""
	logger.info("[rl_grant] grant %s day(s) for %s valid from %s", flt(days), employee, valid_from)
	from hrms.hr.doctype.replacement_leave_claim.replacement_leave_claim import REPLACEMENT_LEAVE_TYPE

	days = flt(days)
	leave_period = get_leave_period(valid_from, valid_from, company)
	if not leave_period:
		frappe.throw(
			_("No active Leave Period covers {0} — create one before approving.").format(
				frappe.bold(str(valid_from))
			)
		)
	allocation = _existing_rl_allocation(employee, REPLACEMENT_LEAVE_TYPE, valid_from)
	if allocation:
		# ponytail: tops up whatever RL allocation covers the period, a mirrored
		# (source-owned) one included. There is no clobber-proof alternative: a hub-
		# native allocation would need a hub name to survive a pull, but the overlap
		# guard (leave_allocation.validate_allocation_overlap) forbids a second
		# allocation of the same type/period, so we cannot sit one beside a mirrored
		# row. Safe under the current workflow — the manual weekend sync imports new
		# companies, it does not re-pull existing employees' Leave Allocations. The
		# one thing that WOULD lose this top-up is a full re-pull of Leave Allocation
		# from the source; before ever doing that, release the mirrored stamp on
		# these rows (hrms.sync.purge.release_instance_stamp) so the source can't
		# reclaim them. See test_utils / the RL cancel path for the reverse side.
		#
		# persisting total into new mirrors CompensatoryLeaveRequest, drift-free while
		# the leave type keeps is_carry_forward=0 (as the ensure patch creates it)
		allocation.new_leaves_allocated += days
		allocation.validate()
		allocation.db_set("new_leaves_allocated", allocation.total_leaves_allocated)
		allocation.db_set("total_leaves_allocated", allocation.total_leaves_allocated)
		create_additional_leave_ledger_entry(allocation, days, valid_from)
		return allocation.name
	is_carry_forward = frappe.db.get_value("Leave Type", REPLACEMENT_LEAVE_TYPE, "is_carry_forward")
	allocation = frappe.get_doc(
		dict(
			doctype="Leave Allocation",
			employee=employee,
			employee_name=employee_name,
			leave_type=REPLACEMENT_LEAVE_TYPE,
			from_date=valid_from,
			to_date=leave_period[0].to_date,
			carry_forward=cint(is_carry_forward),
			new_leaves_allocated=days,
			total_leaves_allocated=days,
			description=description,
		)
	)
	allocation.insert(ignore_permissions=True)
	allocation.submit()
	return allocation.name


def _reversible_days(total_allocated, taken, requested):
	"""Days of a grant that can be clawed back WITHOUT dropping the allocation
	below leave the employee has already taken — reversing past that would leave a
	negative available balance for days that were legitimately used.

	Pure — no DB, plain floats — so it is unit-testable without a bench."""
	return min(float(requested or 0.0), max(0.0, float(total_allocated or 0.0) - float(taken or 0.0)))


def reverse_replacement_leave(allocation_name, days):
	"""Undo a grant_replacement_leave top-up when the source request is cancelled.

	Two things make the naive reversal freeze the cancel, both handled here:

	  * Clamp to what is still unused. A day already taken can't be un-taken, so
	    reverse only the remainder (get_approved_leaves_for_period is the same
	    "taken" the balance is measured against) and tell HR about the rest.
	    Prevents a silent negative available balance.

	  * Do NOT re-validate the allocation. A reversal only ever REDUCES the
	    allocation, so the growth guards don't apply — and set_total_leaves_allocated
	    throws "Total leaves allocated is mandatory" the moment a sole grant is
	    reversed to zero (Replacement Leave is neither earned nor compensatory),
	    which would freeze the cancel even when nothing was taken. Decrement
	    straight through db_set. unused_leaves stays 0 (the leave type is
	    is_carry_forward=0, per ensure_replacement_leave_type), so total == new.
	"""
	from hrms.hr.doctype.leave_application.leave_application import get_approved_leaves_for_period

	days = flt(days)
	allocation = frappe.get_doc("Leave Allocation", allocation_name)
	taken = flt(
		get_approved_leaves_for_period(
			allocation.employee, allocation.leave_type, allocation.from_date, allocation.to_date
		)
	)
	to_reverse = flt(_reversible_days(allocation.total_leaves_allocated, taken, days))
	logger.info(
		"[rl_grant] reverse %s of %s day(s) from %s (taken %s)", to_reverse, days, allocation_name, taken
	)
	if to_reverse < days:
		msg = _(
			"Reversed {0} of {1} day(s) — {2} day(s) of Replacement Leave were already taken and stay allocated."
		).format(to_reverse, days, flt(days - to_reverse))
		frappe.msgprint(msg)
		# Queryable trail for HR reconciliation: the msgprint is transient and the
		# logger line isn't in Desk, so stamp the un-reversed amount onto the
		# allocation's timeline — that is where HR lands when a balance looks off.
		allocation.add_comment("Comment", msg)
	if not to_reverse:
		return
	new_total = max(0.0, flt(allocation.new_leaves_allocated) - to_reverse)
	allocation.db_set("new_leaves_allocated", new_total)
	allocation.db_set("total_leaves_allocated", new_total)
	# writes the negative ledger delta; mutates in-memory new_leaves_allocated, so it
	# must come AFTER the db_set that persists the real remaining balance.
	create_additional_leave_ledger_entry(allocation, to_reverse * -1, getdate())


def get_expected_allocation_date_for_period(
	frequency, allocate_on_day, date, date_of_joining=None, effective_from=None
):
	try:
		doj = date_of_joining.replace(month=date.month, year=date.year)
	except (ValueError, AttributeError):
		doj = datetime.date(date.year, date.month, calendar.monthrange(date.year, date.month)[1])

	if frequency == "Half-Yearly" and effective_from:
		period_start, period_end = get_half_year_periods(date, effective_from)
		half_yearly_dates = {
			"First Day": period_start,
			"Last Day": period_end,
		}
	else:
		half_yearly_dates = {
			"First Day": get_semester_start(date),
			"Last Day": get_semester_end(date),
		}

	return {
		"Monthly": {
			"First Day": get_first_day(date),
			"Last Day": get_last_day(date),
			"Date of Joining": doj,
		},
		"Quarterly": {
			"First Day": get_quarter_start(date),
			"Last Day": get_quarter_ending(date),
		},
		"Half-Yearly": half_yearly_dates,
		"Yearly": {"First Day": get_year_start(date), "Last Day": get_year_ending(date)},
	}[frequency][allocate_on_day]


def get_salary_assignments(employee, payroll_period):
	start_date, end_date = frappe.db.get_value("Payroll Period", payroll_period, ["start_date", "end_date"])
	assignments = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1, "from_date": ["between", (start_date, end_date)]},
		fields=["*"],
		order_by="from_date",
	)

	if not assignments or getdate(assignments[0].from_date) > getdate(start_date):
		# if no assignments found for the given period
		# or the assignment has started in the middle of the period
		# get the last one assigned before the period start date
		past_assignment = frappe.get_all(
			"Salary Structure Assignment",
			filters={"employee": employee, "docstatus": 1, "from_date": ["<", start_date]},
			fields=["*"],
			order_by="from_date desc",
			limit=1,
		)

		if past_assignment:
			assignments = past_assignment + assignments

	return assignments


def get_sal_slip_total_benefit_given(employee, payroll_period, component=False):
	total_given_benefit_amount = 0
	start_date = payroll_period.start_date
	end_date = payroll_period.end_date

	ss = frappe.qb.DocType("Salary Slip")
	sd = frappe.qb.DocType("Salary Detail")
	query = (
		frappe.qb.from_(ss)
		.from_(sd)
		.select(Sum(sd.amount).as_("total_amount"))
		.where(
			(ss.employee == employee)
			& (ss.docstatus == 1)
			& (ss.name == sd.parent)
			& (sd.is_flexible_benefit == 1)
			& (sd.parentfield == "earnings")
			& (sd.parenttype == "Salary Slip")
			& (
				ss.start_date.between(start_date, end_date)
				| ss.end_date.between(start_date, end_date)
				| ((ss.start_date < start_date) & (ss.end_date > end_date))
			)
		)
	)

	if component:
		query = query.where(sd.salary_component == component)

	sum_of_given_benefit = query.run(as_dict=True)

	if sum_of_given_benefit and flt(sum_of_given_benefit[0].total_amount) > 0:
		total_given_benefit_amount = sum_of_given_benefit[0].total_amount
	return total_given_benefit_amount


def get_holiday_dates_for_employee(employee, start_date, end_date):
	"""return a list of holiday dates for the given employee between start_date and end_date"""
	# return only date
	holidays = get_holidays_for_employee(employee, start_date, end_date)

	return [cstr(h.holiday_date) for h in holidays]


def get_holidays_for_employee(employee, start_date, end_date, raise_exception=True, only_non_weekly=False):
	"""Get Holidays for a given employee

	`employee` (str)
	`start_date` (str or datetime)
	`end_date` (str or datetime)
	`raise_exception` (bool)
	`only_non_weekly` (bool)

	return: list of dicts with `holiday_date` and `description`
	"""
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=raise_exception)

	if not holiday_list:
		return []

	filters = {"parent": holiday_list, "holiday_date": ("between", [start_date, end_date])}

	if only_non_weekly:
		filters["weekly_off"] = False

	holidays = frappe.get_all(
		"Holiday", fields=["description", "holiday_date"], filters=filters, order_by="holiday_date"
	)

	return holidays


@erpnext.allow_regional
def calculate_annual_eligible_hra_exemption(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}


@erpnext.allow_regional
def calculate_hra_exemption_for_period(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}


@erpnext.allow_regional
def calculate_tax_with_marginal_relief(tax_slab, tax_amount, annual_taxable_earning):
	# Don't delete this method, used for localization
	# Indian TDS Calculation
	return None


def get_previous_claimed_amount(employee, payroll_period, non_pro_rata=False, component=False):
	total_claimed_amount = 0
	ebc = frappe.qb.DocType("Employee Benefit Claim")
	query = (
		frappe.qb.from_(ebc)
		.select(Sum(ebc.claimed_amount).as_("total_amount"))
		.where(
			(ebc.employee == employee)
			& (ebc.docstatus == 1)
			& (ebc.claim_date.between(payroll_period.start_date, payroll_period.end_date))
		)
	)
	if non_pro_rata:
		query = query.where(ebc.pay_against_benefit_claim == 1)
	if component:
		query = query.where(ebc.earning_component == component)

	sum_of_claimed_amount = query.run(as_dict=True)
	if sum_of_claimed_amount and flt(sum_of_claimed_amount[0].total_amount) > 0:
		total_claimed_amount = sum_of_claimed_amount[0].total_amount
	return total_claimed_amount


def share_doc_with_approver(doc, user):
	if not user:
		return

	# if approver does not have permissions, share
	if not frappe.has_permission(doc=doc, ptype="submit", user=user):
		frappe.share.add_docshare(
			doc.doctype, doc.name, user, submit=1, flags={"ignore_share_permission": True}
		)

		frappe.msgprint(
			_("Shared document with the user {0} with 'Submit' permission").format(user), alert=True
		)

	# remove shared doc if approver changes
	doc_before_save = doc.get_doc_before_save()
	if doc_before_save:
		approvers = {
			"Leave Application": "leave_approver",
			"Expense Claim": "expense_approver",
			"Shift Request": "approver",
		}

		approver = approvers.get(doc.doctype)
		if doc_before_save.get(approver) != doc.get(approver):
			frappe.share.remove(doc.doctype, doc.name, doc_before_save.get(approver))


def validate_self_submission(doc):
	"""Doctypes with no approver/status flow treat submission AS the approval —
	the employee on the request must never be the submitter, whatever roles
	they hold. Mirrors AttendanceRequest.validate_for_self_approval; sites that
	attach a Workflow govern self-approval through it instead."""
	logger.info("[self_submission] fence: %s %s", doc.doctype, doc.name)
	from frappe.model.workflow import get_workflow_name

	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if employee_user == frappe.session.user and not get_workflow_name(doc.doctype):
		logger.warning("[self_submission] blocked: %s %s by %s", doc.doctype, doc.name, frappe.session.user)
		frappe.throw(_("Self-approval for {0} is not allowed").format(_(doc.doctype)))


def validate_filing_for_self(doc):
	"""Doctypes without an approver field carry no routing to catch a request
	forged in a colleague's name — so non-HR users may only file for their own
	Employee record. HR roles and users with real Employee write access are
	exempt (they file on staff's behalf legitimately)."""
	logger.info("[self_submission] filing fence: %s %s", doc.doctype, doc.name)
	user = frappe.session.user
	if user == "Administrator" or HR_ROLES & set(frappe.get_roles(user)):
		return
	if frappe.db.get_value("Employee", doc.employee, "user_id") == user:
		return
	if frappe.has_permission("Employee", ptype="write", doc=doc.employee):
		return
	logger.warning("[self_submission] %s tried to file %s for employee %s", user, doc.doctype, doc.employee)
	frappe.throw(_("You can only file requests for yourself."), frappe.PermissionError)


def validate_mandatory_attachment(doc):
	"""Requests may be required to carry supporting evidence (a stored file, not
	just a File row) before an approver can submit them — gated by the HR Setting
	`require_supporting_attachment`, off by default (HR confirmed these requests
	do not always need evidence)."""
	if not frappe.utils.cint(frappe.db.get_single_value("HR Settings", "require_supporting_attachment")):
		return
	if not frappe.db.exists(
		"File",
		{
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"file_url": ("is", "set"),
		},
	):
		logger.info("[self_submission] submit blocked, no attachment: %s %s", doc.doctype, doc.name)
		frappe.throw(_("A supporting attachment is required before this request can be approved"))


def get_direct_report_employees(user: str) -> list[str]:
	"""Active employees reporting directly to any of this user's ACTIVE employees.

	One definition of "my team", shared by every row scope that grants a manager
	sight of their reports — duplicating it would let the fences drift apart.

	Both sides are status-filtered: an offboarded manager whose User account is
	still enabled keeps nothing, and inactive reports drop out.

	Narrowed to the manager's permitted companies when they carry a Company User
	Permission. A manager fenced to one company must not read another company's
	records just because the reporting line crosses the boundary; a manager with
	no Company UP is unfenced, matching hrms.overrides.company_scope.
	"""
	from hrms.overrides.company_scope import allowed_companies
	from hrms.utils.identity import own_employees

	# Canonical identity for the manager's own record too: a case-drifted mirror
	# user_id no longer hides a manager's whole team, and two Active rows fail
	# closed instead of unioning two people's reporting lines.
	own = own_employees(user)
	if not own:
		return []

	filters = {"reports_to": ("in", own), "status": "Active"}
	companies = allowed_companies(user)
	if companies:
		filters["company"] = ("in", companies)

	reports = frappe.get_all("Employee", filters=filters, pluck="name")
	logger.debug(
		"[team_scope] %s manages %d direct report(s), company fence=%s",
		user,
		len(reports),
		companies or "none",
	)
	return reports


def get_designated_approvers(
	employee: str, employee_approver_field: str, department_parentfield: str
) -> list[str]:
	"""Who this employee may route a request to. THE source of truth.

	Both the PWA's approver selector and the server-side fence
	(`validate_staff_approver`) read this list, because when they disagree the
	form offers a choice the save then rejects — which is what
	"{0} is not one of your designated approvers" looked like from the
	employee's side.

	The set is deliberately narrow: the explicit approver on the Employee
	record, the reporting manager, and the approvers named on the employee's
	OWN department. It does not walk up the department tree. Nothing in this
	repo or in the donor branch says a parent-department approver may approve
	for a child department, so the fence keeps the narrower boundary until HR
	says otherwise; widening it would hand approval authority to people nobody
	has authorised.

	The employee's own user is never included — self-approval is refused
	separately, with its own message.
	"""
	info = frappe.db.get_value(
		"Employee",
		employee,
		["user_id", employee_approver_field, "reports_to", "department"],
		as_dict=True,
	)
	if not info:
		logger.warning("[staff_lockdown] no Employee %s while resolving approvers", employee)
		return []

	approvers = []
	if info.get(employee_approver_field):
		approvers.append(info.get(employee_approver_field))
	if info.reports_to:
		if manager_user := frappe.db.get_value("Employee", info.reports_to, "user_id"):
			approvers.append(manager_user)
	if info.department:
		approvers.extend(
			frappe.get_all(
				"Department Approver",
				filters={"parent": info.department, "parentfield": department_parentfield},
				pluck="approver",
			)
		)

	# de-duplicate but keep order: the Employee-record approver is the default
	seen = set()
	ordered = []
	for approver in approvers:
		if approver and approver != info.user_id and approver not in seen:
			seen.add(approver)
			ordered.append(approver)

	logger.info(
		"[staff_lockdown] %s designated approver(s) for %s via %s",
		len(ordered),
		employee,
		department_parentfield,
	)
	return ordered


def validate_staff_approver(doc, approver_field, employee_approver_field, department_parentfield):
	"""Staff lockdown: when the applicant edits their own request, the approver
	must be one of their designated approvers (reporting manager, the explicit
	approver on their Employee record, or a department approver) — never
	themselves. HR roles and other editors (e.g. the approver) are exempt;
	doctype permissions govern those.
	"""
	logger.info("[staff_lockdown] approver fence: %s.%s", doc.doctype, approver_field)
	approver = doc.get(approver_field)
	if not approver:
		return

	user = frappe.session.user
	if user == "Administrator" or HR_ROLES & set(frappe.get_roles(user)):
		return

	info = frappe.db.get_value(
		"Employee",
		doc.employee,
		["user_id", employee_approver_field, "reports_to", "department"],
		as_dict=True,
	)
	if not info:
		frappe.throw(_("Employee {0} not found.").format(doc.employee))

	if info.user_id != user:
		# the designated approver acts on someone else's request legitimately
		# (approve/submit sets status + docstatus, which re-runs validate).
		# Trust only the value ALREADY STORED on the document — reading the
		# incoming payload would let anyone name themselves approver in the
		# same save and walk through this fence.
		if not doc.is_new() and frappe.db.get_value(doc.doctype, doc.name, approver_field) == user:
			logger.info("[staff_lockdown] %s acting as stored approver on %s %s", user, doc.doctype, doc.name)
			return

		# filing for someone else — fail CLOSED. Own-record scoping normally
		# comes from a User Permission, but that binding has broken before on
		# this fork, so never fall through to "no checks at all" here.
		if not frappe.has_permission("Employee", ptype="write", doc=doc.employee):
			logger.warning(
				"[staff_lockdown] %s tried to file %s for employee %s", user, doc.doctype, doc.employee
			)
			frappe.throw(
				_("You can only submit requests for yourself."),
				frappe.PermissionError,
			)
		return

	if approver == user:
		logger.warning("[staff_lockdown] %s attempted self-approval routing on %s", user, doc.doctype)
		frappe.throw(_("You cannot set yourself as your own approver."))

	# same list the PWA selector is built from — see get_designated_approvers
	allowed = set(get_designated_approvers(doc.employee, employee_approver_field, department_parentfield))

	if approver not in allowed:
		logger.warning(
			"[staff_lockdown] %s set non-designated approver %s on %s %s (allowed=%s)",
			user,
			approver,
			doc.doctype,
			doc.name,
			sorted(allowed),
		)
		frappe.throw(
			_("{0} is not one of your designated approvers. Please select your reporting manager.").format(
				approver
			)
		)


def validate_active_employee(employee, method=None):
	if isinstance(employee, dict | Document):
		employee = employee.get("employee")

	if employee and frappe.db.get_value("Employee", employee, "status") == "Inactive":
		frappe.throw(
			_("Transactions cannot be created for an Inactive Employee {0}.").format(
				get_link_to_form("Employee", employee)
			),
			InactiveEmployeeStatusError,
		)


def validate_loan_repay_from_salary(doc, method=None):
	if doc.applicant_type == "Employee" and doc.repay_from_salary:
		from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
			get_employee_currency,
		)

		if not doc.applicant:
			frappe.throw(_("Please select an Applicant"))

		if not doc.company:
			frappe.throw(_("Please select a Company"))

		employee_currency = get_employee_currency(doc.applicant)
		company_currency = erpnext.get_company_currency(doc.company)
		if employee_currency != company_currency:
			frappe.throw(
				_(
					"Loan cannot be repayed from salary for Employee {0} because salary is processed in currency {1}"
				).format(doc.applicant, employee_currency)
			)

	if not doc.is_term_loan and doc.repay_from_salary:
		frappe.throw(_("Repay From Salary can be selected only for term loans"))


def get_matching_queries(
	bank_account,
	company,
	transaction,
	document_types,
	exact_match,
	account_from_to=None,
	from_date=None,
	to_date=None,
	filter_by_reference_date=None,
	from_reference_date=None,
	to_reference_date=None,
	common_filters=None,
):
	"""Returns matching queries for Bank Reconciliation"""
	queries = []
	if transaction.withdrawal > 0:
		if "expense_claim" in document_types:
			ec_amount_matching = get_ec_matching_query(
				bank_account, company, exact_match, from_date, to_date, common_filters
			)
			queries.extend([ec_amount_matching])

	return queries


def get_ec_matching_query(
	bank_account, company, exact_match, from_date=None, to_date=None, common_filters=None
):
	# get matching Expense Claim query
	filters = []
	ec = qb.DocType("Expense Claim")

	mode_of_payments = [
		x["parent"]
		for x in frappe.db.get_all(
			"Mode of Payment Account", filters={"default_account": bank_account}, fields=["parent"]
		)
	]
	company_currency = get_company_currency(company)

	filters.append(ec.docstatus == 1)
	filters.append(ec.is_paid == 1)
	filters.append(ec.clearance_date.isnull())
	if mode_of_payments:
		filters.append(ec.mode_of_payment.isin(mode_of_payments))

	if common_filters:
		ref_rank = frappe.qb.terms.Case().when(ec.employee == common_filters.party, 1).else_(0) + 1

		if exact_match:
			filters.append(ec.total_amount_reimbursed == common_filters.amount)
		else:
			filters.append(ec.total_amount_reimbursed.gt(common_filters.amount))
	else:
		ref_rank = ConstantColumn(1)

	if from_date and to_date:
		filters.append(ec.posting_date[from_date:to_date])

	ec_query = (
		qb.from_(ec)
		.select(
			ref_rank.as_("rank"),
			ConstantColumn("Expense Claim").as_("doctype"),
			ec.name,
			ec.total_sanctioned_amount.as_("paid_amount"),
			ConstantColumn("").as_("reference_no"),
			ConstantColumn("").as_("reference_date"),
			ec.employee.as_("party"),
			ConstantColumn("Employee").as_("party_type"),
			ec.posting_date,
			ConstantColumn(company_currency).as_("currency"),
		)
		.where(Criterion.all(filters))
	)

	if from_date and to_date:
		ec_query = ec_query.orderby(ec.posting_date)

	return ec_query


def validate_bulk_tool_fields(
	self, fields: list, employees: list, from_date: str | None = None, to_date: str | None = None
) -> None:
	for d in fields:
		if not self.get(d):
			frappe.throw(_("{0} is required").format(_(self.meta.get_label(d))), title=_("Missing Field"))
	if self.get(from_date) and self.get(to_date):
		self.validate_from_to_dates(from_date, to_date)
	if not employees:
		frappe.throw(
			_("Please select at least one employee to perform this action."),
			title=_("No Employees Selected"),
		)


def notify_bulk_action_status(doctype: str, failure: list, success: list) -> None:
	frappe.clear_messages()

	msg = ""
	title = ""
	if failure:
		msg += _("Failed to create/submit {0} for employees:").format(doctype)
		msg += " " + comma_and(failure, False) + "<hr>"
		msg += (
			_("Check {0} for more details")
			.format("<a href='/app/List/Error Log?reference_doctype={0}'>{1}</a>")
			.format(doctype, _("Error Log"))
		)

		if success:
			title = _("Partial Success")
			msg += "<hr>"
		else:
			title = _("Creation Failed")
	else:
		title = _("Success")

	if success:
		msg += _("Successfully created {0} for employees:").format(doctype)
		msg += " " + comma_and(success, False)

	if failure:
		indicator = "orange" if success else "red"
	else:
		indicator = "green"

	frappe.msgprint(
		msg,
		indicator=indicator,
		title=title,
		is_minimizable=True,
	)


@frappe.whitelist()
def set_geolocation_from_coordinates(doc: Document):
	# Per company where the doc names one. Called for BOTH Employee Checkin
	# (which names an employee) and Shift Location (a master, which names
	# neither) — an unresolved company falls through to the global value, so
	# the Shift Location path behaves exactly as it did.
	from hrms.utils.company_settings import employee_company, is_company_setting_enabled

	company = employee_company(doc.get("employee")) or doc.get("company")
	if not is_company_setting_enabled(company, "allow_geolocation_tracking"):
		return

	if not (doc.latitude and doc.longitude):
		return

	doc.geolocation = frappe.json.dumps(
		{
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"properties": {},
					# geojson needs coordinates in reverse order: long, lat instead of lat, long
					"geometry": {"type": "Point", "coordinates": [doc.longitude, doc.latitude]},
				}
			],
		}
	)


def get_distance_between_coordinates(lat1, long1, lat2, long2):
	from math import asin, cos, pi, sqrt

	r = 6371
	p = pi / 180

	a = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((long2 - long1) * p)) / 2
	return 2 * r * asin(sqrt(a)) * 1000


def check_app_permission():
	"""Check if user has permission to access the app (for showing the app on app screen)"""
	if frappe.session.user == "Administrator":
		return True

	# Website Users cannot access desk routes, so don't show the app to them
	# This prevents redirect to /desk/people followed by 403 Forbidden
	user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")
	if user_type == "Website User":
		return False

	if frappe.has_permission("Employee", ptype="read"):
		return True

	return False


def get_exact_month_diff(string_ed_date: DateTimeLikeObject, string_st_date: DateTimeLikeObject) -> int:
	"""Return the difference between given two dates in months."""
	ed_date = getdate(string_ed_date)
	st_date = getdate(string_st_date)
	diff = (ed_date.year - st_date.year) * 12 + ed_date.month - st_date.month

	# count the last month only if end date's day > start date's day
	# to handle cases like 16th Jul 2024 - 15th Jul 2025
	# where framework's month_diff will calculate diff as 13 months
	if ed_date.day >= st_date.day:
		diff += 1
	return diff


def get_semester_start(date):
	if date.month <= 6:
		return get_year_start(date)
	else:
		return add_months(get_year_start(date), 6)


def get_semester_end(date):
	if date.month > 6:
		return get_year_ending(date)
	else:
		return add_months(get_year_ending(date), -6)


def get_complete_month_count(date, effective_from):
	"""Returns count of complete months from effective_from to date, accounting for day-of-month."""
	month_count = (date.year - effective_from.year) * 12 + (date.month - effective_from.month)
	# ignore a smaller day caused by a shorter month (e.g. 31st -> 28th)
	if date.day < effective_from.day and date != get_last_day(date):
		month_count -= 1
	return month_count


def get_half_year_periods(date, effective_from):
	"""Return (start, end) of the half-year period containing date, relative to effective_from."""
	effective_from = getdate(effective_from)
	date = getdate(date)

	half_years_passed = get_complete_month_count(date, effective_from) // 6

	half_year_start = add_months(effective_from, half_years_passed * 6)
	half_year_end = add_days(add_months(half_year_start, 6), -1)

	return half_year_start, half_year_end
