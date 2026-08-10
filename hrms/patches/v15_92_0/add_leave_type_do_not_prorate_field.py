"""Add the Leave Type "Do Not Pro-rate on Policy Assignment" checkbox.

Backs hrms.overrides.leave_policy_assignment_override.CustomLeavePolicyAssignment:
leave types with this checked (e.g. Medical Leave, Hospitalization Leave under
Malaysian Employment Act practice) allocate the FULL annual amount even when the
employee joins mid-way through the leave period. Unchecked / missing → standard
HRMS pro-rating. Ignored for Earned and Compensatory leave types, whose
allocation cycles are managed separately.

Safe to re-run; create_custom_fields with update=True is idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Leave Type": [
				{
					"fieldname": "custom_do_not_prorate",
					"fieldtype": "Check",
					"label": "Do Not Pro-rate on Policy Assignment",
					"insert_after": "include_holiday",
					"default": "0",
					"description": (
						"When checked, Leave Policy Assignment allocates the full "
						"annual amount for this leave type even if the employee "
						"joins mid-way through the leave period (no pro-rating). "
						"Has no effect on Earned or Compensatory leave types."
					),
					"module": "HR",
					"translatable": 0,
				}
			],
		},
		update=True,
	)
	frappe.db.commit()
