"""Leave Policy Assignment override: per-leave-type opt-out from pro-rating.

Wired via override_doctype_class in hooks.py. When a Leave Type has the custom
checkbox "Do Not Pro-rate on Policy Assignment" (custom_do_not_prorate, added by
hrms.patches.v15_92_0.add_leave_type_do_not_prorate_field) checked, granting a
Leave Policy Assignment allocates the FULL annual amount for that type even if
the employee's date of joining falls inside the leave period. Everything else —
earned-leave accrual, compensatory leaves, and pro-rating of unflagged types —
delegates to the stock HRMS implementation.

Covers every grant path, since all of them run through get_new_leaves():
- single Leave Policy Assignment submit
- bulk create_assignment_for_multiple_employees
- the grade-driven auto assignment job in hrms.hr.leave_rules

Also fixes the "Joining Date" basis window (see set_dates): the allocation
covers the CURRENT anniversary year instead of starting at the historical DOJ,
which is also what makes the service-band (years-of-service) lookup evaluate
tenure correctly instead of always resolving to 0 completed years.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, formatdate, getdate

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment


def current_service_anniversary(date_of_joining, as_on=None):
	"""The employee's most recent joining anniversary on or before `as_on`
	(default: today) — i.e. DOJ shifted forward by the completed years of
	service. For a brand-new joiner this is the DOJ itself."""
	from dateutil.relativedelta import relativedelta

	date_of_joining = getdate(date_of_joining)
	as_on = getdate(as_on) if as_on else (getdate(frappe.flags.current_date) or getdate())
	completed_years = max(relativedelta(as_on, date_of_joining).years, 0)
	return date_of_joining + relativedelta(years=completed_years)


class CustomLeavePolicyAssignment(LeavePolicyAssignment):
	def set_dates(self):
		"""TENURE/WINDOW RULE (fixes the "everyone lands in the 0-2 band" bug):

		For assignment_based_on == "Joining Date" the allocation window is the
		CURRENT anniversary year — effective_from = the employee's most recent
		joining anniversary, effective_to = anniversary + 12 months - 1 day
		(e.g. DOJ 2021-12-20 -> 2025-12-20..2026-12-19). Both dates are forced;
		a caller-supplied effective_to is exactly what produced the historical
		five-year DOJ..year-end windows. Stock behavior (raw DOJ as
		effective_from) made the service-band lookup evaluate tenure at the DOJ
		itself, which is always 0 completed years.

		Years of service are therefore evaluated as at effective_from: the
		current anniversary for the Joining Date basis, the leave period start
		for the Leave Period basis (unchanged stock dates for every other basis).
		"""
		supplied_to = getdate(self.effective_to) if self.effective_to else None

		super().set_dates()

		if self.assignment_based_on != "Joining Date":
			return

		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if not date_of_joining:
			return

		anniversary = current_service_anniversary(date_of_joining)
		computed_to = add_days(add_months(anniversary, 12), -1)
		frappe.logger("hrms").info(
			"[leave_policy_assignment_override] %s: Joining Date window normalized from (%s, %s) to (%s, %s)",
			self.employee,
			self.effective_from,
			self.effective_to,
			anniversary,
			computed_to,
		)
		if supplied_to and supplied_to != computed_to:
			# surface the normalization instead of silently discarding the
			# supplied end date (also fires when a draft's window rolls over
			# to the next anniversary before submission)
			frappe.msgprint(
				_(
					"Effective dates follow the current joining-anniversary year: {0} to {1}. "
					"The supplied end date {2} was replaced."
				).format(formatdate(anniversary), formatdate(computed_to), formatdate(supplied_to)),
				indicator="orange",
				alert=True,
			)
		self.effective_from = anniversary
		self.effective_to = computed_to

	def get_new_leaves(self, annual_allocation, leave_details, date_of_joining):
		if self.should_skip_proration(leave_details):
			from frappe.model.meta import get_field_precision

			precision = get_field_precision(
				frappe.get_meta("Leave Allocation").get_field("new_leaves_allocated")
			)
			frappe.logger("hrms").info(
				"[leave_policy_assignment_override] %s: allocating full %s for %s "
				"(custom_do_not_prorate=1, pro-rating skipped)",
				self.employee,
				annual_allocation,
				leave_details.name,
			)
			return flt(annual_allocation, precision)

		return super().get_new_leaves(annual_allocation, leave_details, date_of_joining)

	def should_skip_proration(self, leave_details):
		# Earned and Compensatory allocations follow their own scheduler-driven
		# cycles — the opt-out only bypasses plain calendar pro-rating.
		if leave_details.is_earned_leave or leave_details.is_compensatory:
			return False
		# doc.get() (via get_cached_value) returns None when the custom field
		# has not been installed yet, so sites without the patch keep stock behavior.
		return bool(frappe.get_cached_value("Leave Type", leave_details.name, "custom_do_not_prorate"))
