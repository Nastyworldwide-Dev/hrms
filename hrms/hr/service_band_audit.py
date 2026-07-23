"""Audit report for service-banded allocations created with the wrong band.

Before the set_dates fix in leave_policy_assignment_override, "Joining Date"
basis assignments evaluated tenure at the raw date of joining (always 0
completed years) and opened multi-year DOJ-anchored allocation windows. This
module finds the submitted Leave Allocations still carrying those wrong values
so HR can cancel and re-assign the affected employees. Read-only — it never
mutates anything.

Run it any of these ways (no arguments needed):
  bench --site {site} execute hrms.hr.service_band_audit.find_misbanded_allocations
  POST /api/method/hrms.hr.service_band_audit.find_misbanded_allocations

Known limitation: expected values are computed from the employee's CURRENT
grade and date of joining (mirroring how granting itself works), so an
allocation that was correct under a since-changed grade will be flagged —
review the rows before cancelling.
"""

import frappe
from frappe.utils import add_days, add_months, flt, formatdate, getdate

from hrms.hr.doctype.leave_type.leave_type import get_service_based_leave_days
from hrms.overrides.leave_policy_assignment_override import current_service_anniversary


@frappe.whitelist()
def find_misbanded_allocations() -> list[dict]:
	"""Every submitted Leave Allocation created by a "Joining Date" basis Leave
	Policy Assignment for a service-banded leave type, where the window or the
	allocated days differ from what the fixed rules produce today."""
	frappe.only_for(("System Manager", "HR Manager"))

	banded_leave_types = frappe.get_all("Leave Type", filters={"based_on_years_of_service": 1}, pluck="name")
	if not banded_leave_types:
		return []

	allocations = frappe.get_all(
		"Leave Allocation",
		filters={
			"docstatus": 1,
			"leave_type": ("in", banded_leave_types),
			"leave_policy_assignment": ("is", "set"),
		},
		fields=[
			"name",
			"employee",
			"employee_name",
			"leave_type",
			"leave_policy",
			"leave_policy_assignment",
			"from_date",
			"to_date",
			"new_leaves_allocated",
		],
	)

	rows = []
	for allocation in allocations:
		basis, date_of_joining, grade = _assignment_context(allocation)
		if basis != "Joining Date" or not date_of_joining:
			continue

		anniversary = current_service_anniversary(date_of_joining)
		expected_from = anniversary
		expected_to = add_days(add_months(anniversary, 12), -1)
		expected_days = _expected_days(allocation, date_of_joining, anniversary, grade)

		reasons = []
		if getdate(allocation.from_date) != expected_from or getdate(allocation.to_date) != expected_to:
			reasons.append("window is not the current anniversary year")
		if expected_days is not None and flt(allocation.new_leaves_allocated) != flt(expected_days):
			reasons.append("allocated days do not match the service band")

		if reasons:
			rows.append(
				{
					"employee": allocation.employee,
					"employee_name": allocation.employee_name,
					"leave_type": allocation.leave_type,
					"leave_allocation": allocation.name,
					"leave_policy_assignment": allocation.leave_policy_assignment,
					"current_days": flt(allocation.new_leaves_allocated),
					"expected_days": expected_days,
					"current_window": f"{formatdate(allocation.from_date)} - {formatdate(allocation.to_date)}",
					"expected_window": f"{formatdate(expected_from)} - {formatdate(expected_to)}",
					"reasons": reasons,
				}
			)

	frappe.logger("hrms").info(
		"[service_band_audit] checked %s banded allocations, flagged %s", len(allocations), len(rows)
	)
	return rows


def _assignment_context(allocation):
	basis, employee = frappe.db.get_value(
		"Leave Policy Assignment",
		allocation.leave_policy_assignment,
		["assignment_based_on", "employee"],
	) or (None, None)
	if not employee:
		return None, None, None

	date_of_joining, grade = frappe.db.get_value("Employee", employee, ["date_of_joining", "grade"]) or (
		None,
		None,
	)
	return basis, date_of_joining, grade


def _expected_days(allocation, date_of_joining, anniversary, grade):
	"""Band days at the corrected tenure date, falling back to the policy's
	annual allocation when no slab covers the employee (mirrors the grant path;
	no pro-ration applies on the Joining Date basis since the window starts on
	the anniversary)."""
	expected = get_service_based_leave_days(allocation.leave_type, date_of_joining, anniversary, grade)
	if expected is None and allocation.leave_policy:
		expected = frappe.db.get_value(
			"Leave Policy Detail",
			{"parent": allocation.leave_policy, "leave_type": allocation.leave_type},
			"annual_allocation",
		)
	return flt(expected) if expected is not None else None
