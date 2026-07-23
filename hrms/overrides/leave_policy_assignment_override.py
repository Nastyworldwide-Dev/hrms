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
"""

import frappe
from frappe.utils import flt

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment


class CustomLeavePolicyAssignment(LeavePolicyAssignment):
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
