# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from itertools import pairwise

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import getdate, today


class LeaveType(Document):
	def validate(self):
		self.validate_lwp()
		self.validate_leave_types()
		self.validate_allocated_earned_leave()
		self.validate_service_entitlements()

	def validate_lwp(self):
		if self.is_lwp:
			leave_allocation = frappe.get_all(
				"Leave Allocation",
				filters={"leave_type": self.name, "from_date": ("<=", today()), "to_date": (">=", today())},
				fields=["name"],
			)
			leave_allocation = [l["name"] for l in leave_allocation]
			if leave_allocation:
				frappe.throw(
					_(
						"Leave application is linked with leave allocations {0}. Leave application cannot be set as leave without pay"
					).format(", ".join(leave_allocation))
				)  # nosec

	def validate_leave_types(self):
		if self.is_compensatory and self.is_earned_leave:
			msg = _("Leave Type can either be compensatory or earned leave.") + "<br><br>"
			msg += _("Earned Leaves are allocated as per the configured frequency via scheduler.") + "<br>"
			msg += _(
				"Whereas allocation for Compensatory Leaves is automatically created or updated on submission of Compensatory Leave Request."
			)
			msg += "<br><br>"
			msg += _("Disable {0} or {1} to proceed.").format(
				bold(_("Is Compensatory Leave")), bold(_("Is Earned Leave"))
			)
			frappe.throw(msg, title=_("Not Allowed"))

		if self.is_lwp and self.is_ppl:
			frappe.throw(_("Leave Type can either be without pay or partial pay"), title=_("Not Allowed"))

		if self.is_ppl and (
			self.fraction_of_daily_salary_per_leave < 0 or self.fraction_of_daily_salary_per_leave > 1
		):
			frappe.throw(_("The fraction of Daily Salary per Leave should be between 0 and 1"))

	def validate_allocated_earned_leave(self):
		old_configuration = self.get_doc_before_save()

		if (
			old_configuration
			and old_configuration.is_earned_leave
			and old_configuration.max_leaves_allowed > self.max_leaves_allowed
		):
			earned_leave_allocation_exists = frappe.db.exists(
				"Leave Allocation",
				{"leave_type": self.name, "from_date": ("<=", today()), "to_date": (">=", today())},
				cache=True,
			)
			if earned_leave_allocation_exists:
				frappe.msgprint(
					title=_("Leave Allocation Exists"),
					msg=_(
						"Reducing maximum leaves allowed after allocation may cause scheduler to allocate incorrect number of earned leaves. Proceed with caution."
					),
				)

	def validate_service_entitlements(self):
		if not self.based_on_years_of_service:
			return

		# earned leaves accrue periodically from the policy's annual allocation and
		# compensatory leaves are allocated per request, so slabs cannot apply to them
		if self.is_earned_leave or self.is_compensatory:
			frappe.throw(
				_("{0} cannot be combined with {1} or {2}").format(
					bold(_("Entitlement Based on Years of Service")),
					bold(_("Is Earned Leave")),
					bold(_("Is Compensatory")),
				),
				title=_("Not Allowed"),
			)

		if not self.service_entitlements:
			frappe.throw(
				_("Please add at least one row in the Service Entitlements table"),
				title=_("Service Entitlements Missing"),
			)

		rows_by_grade = {}
		for row in self.service_entitlements:
			# "To" is the exclusive upper bound (e.g. From 0, To 2 means "below 2 years"),
			# so it must be strictly greater than "From"
			if row.to_years <= row.from_years:
				frappe.throw(
					_("Row #{0}: {1} must be greater than {2}").format(
						row.idx, bold(_("To (Years of Service)")), bold(_("From (Years of Service)"))
					)
				)
			rows_by_grade.setdefault(row.grade or "", []).append(row)

		# ranges may overlap across grades, but not within the same grade.
		# adjacent rows are allowed (one row's "To" may equal the next row's "From")
		# since "To" is exclusive
		for rows in rows_by_grade.values():
			rows = sorted(rows, key=lambda row: row.from_years)
			for previous, current in pairwise(rows):
				if current.from_years < previous.to_years:
					frappe.throw(
						_("Row #{0}: Years of service range overlaps with row #{1}").format(
							current.idx, previous.idx
						),
						title=_("Overlapping Service Entitlements"),
					)

	def clear_cache(self):
		from hrms.payroll.doctype.salary_slip.salary_slip import LEAVE_TYPE_MAP

		frappe.cache().delete_value(LEAVE_TYPE_MAP)
		return super().clear_cache()


def get_service_based_leave_days(leave_type: str, date_of_joining, on_date, grade=None) -> float | None:
	"""Returns entitled leave days for the slab matching the employee's completed
	years of service as on `on_date`, or None if no slab covers it.
	A slab covers years_of_service when from_years <= years_of_service < to_years
	("To" is exclusive). A slab for the employee's grade takes precedence over slabs
	without a grade."""
	from dateutil.relativedelta import relativedelta

	if not date_of_joining:
		return None

	years_of_service = relativedelta(getdate(on_date), getdate(date_of_joining)).years
	slabs = frappe.get_all(
		"Leave Type Service Entitlement",
		filters={
			"parenttype": "Leave Type",
			"parent": leave_type,
			"from_years": ("<=", years_of_service),
			"to_years": (">", years_of_service),
		},
		fields=["grade", "leave_days"],
	)

	matched = next((slab for slab in slabs if grade and slab.grade == grade), None) or next(
		(slab for slab in slabs if not slab.grade), None
	)
	leave_days = matched.leave_days if matched else None

	frappe.logger("leave").info(
		"[leave_type] Service-based entitlement for %s: %s completed years, grade %s -> %s days",
		leave_type,
		years_of_service,
		grade,
		leave_days,
	)
	return leave_days


@frappe.whitelist()
def get_service_based_leave_days_for_employee(
	leave_type: str, employee: str, on_date: str | None = None
) -> float | None:
	frappe.has_permission("Employee", "read", doc=employee, throw=True)

	if not frappe.db.get_value("Leave Type", leave_type, "based_on_years_of_service"):
		return None

	date_of_joining, grade = frappe.db.get_value("Employee", employee, ["date_of_joining", "grade"])
	return get_service_based_leave_days(leave_type, date_of_joining, on_date or today(), grade)
