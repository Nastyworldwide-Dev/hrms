# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt

logger = logging.getLogger(__name__)

ALLOWED_ROLES = ("System Manager", "HR Manager", "HR User", "Accounts Manager", "Accounts User")


def execute(filters=None):
	_check_access()
	filters = frappe._dict(filters or {})
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("From Date and To Date are required."))

	slips = _get_salary_slips(filters)
	employer_costs = _get_employer_contributions([s.name for s in slips])
	allocations = _get_employee_allocations({s.employee for s in slips})

	rows = build_allocation_rows(slips, employer_costs, allocations)
	if filters.territory:
		rows = [r for r in rows if r["territory"] == filters.territory]
	logger.info("[interco_report] user=%s slips=%d rows=%d", frappe.session.user, len(slips), len(rows))
	return _get_columns(), rows


def build_allocation_rows(slips, employer_costs, allocations) -> list[dict]:
	"""Split each slip's total employer cost across the employee's interco
	allocations. Pure function — the last allocation row absorbs the
	rounding remainder so the per-employee split always sums exactly.

	Employees without allocation rows appear as a single 100% row with a
	blank Interco so their cost stays visible until the table is filled.
	"""
	rows = []
	for slip in slips:
		contributions = flt(employer_costs.get(slip.name, 0))
		total_cost = flt(slip.gross_pay) + contributions
		employee_allocations = allocations.get(slip.employee) or [{"territory": None, "percentage": 100.0}]

		allocated_so_far = 0.0
		for i, allocation in enumerate(employee_allocations):
			is_last = i == len(employee_allocations) - 1
			amount = (
				round(total_cost - allocated_so_far, 2)
				if is_last
				else round(total_cost * flt(allocation["percentage"]) / 100.0, 2)
			)
			allocated_so_far += amount
			rows.append(
				{
					"employee": slip.employee,
					"employee_name": slip.employee_name,
					"company": slip.company,
					"territory": allocation["territory"],
					"percentage": flt(allocation["percentage"]),
					"gross_pay": flt(slip.gross_pay) if i == 0 else 0,
					"employer_contributions": contributions if i == 0 else 0,
					"total_employer_cost": total_cost if i == 0 else 0,
					"allocated_amount": amount,
				}
			)
	return rows


def _get_salary_slips(filters):
	conditions = {
		"docstatus": 1,
		"start_date": (">=", filters.from_date),
		"end_date": ("<=", filters.to_date),
	}
	if filters.company:
		conditions["company"] = filters.company
	return frappe.get_all(
		"Salary Slip",
		filters=conditions,
		fields=["name", "employee", "employee_name", "company", "gross_pay"],
		order_by="employee asc, start_date asc",
	)


def _get_employer_contributions(slip_names) -> dict:
	"""Employer statutory shares are statistical deduction rows (EPF/SOCSO
	Employer etc.) — they never hit net pay but are real employer cost."""
	if not slip_names:
		return {}
	rows = frappe.get_all(
		"Salary Detail",
		filters={
			"parent": ("in", slip_names),
			"parentfield": "deductions",
			"statistical_component": 1,
		},
		fields=["parent", "sum(amount) as total"],
		group_by="parent",
	)
	return {row.parent: flt(row.total) for row in rows}


def _get_employee_allocations(employees):
	if not employees:
		return {}
	allocation_rows = frappe.get_all(
		"Employee Interco Allocation",
		filters={"parenttype": "Employee", "parent": ("in", list(employees))},
		fields=["parent", "territory", "percentage"],
		order_by="parent asc, idx asc",
	)
	allocations = {}
	for row in allocation_rows:
		allocations.setdefault(row.parent, []).append(
			{"territory": row.territory, "percentage": flt(row.percentage)}
		)
	logger.debug(
		"[interco_report] allocations loaded employees=%d allocated=%d", len(employees), len(allocations)
	)
	return allocations


def _get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 160},
		{
			"fieldname": "company",
			"label": _("Paying Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"fieldname": "territory",
			"label": _("Interco (Territory)"),
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		},
		{"fieldname": "percentage", "label": _("%"), "fieldtype": "Percent", "width": 70},
		{"fieldname": "gross_pay", "label": _("Gross Pay"), "fieldtype": "Currency", "width": 110},
		{
			"fieldname": "employer_contributions",
			"label": _("Employer Contributions"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "total_employer_cost",
			"label": _("Total Employer Cost"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "allocated_amount",
			"label": _("Allocated Amount"),
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def _check_access():
	user = frappe.session.user
	if user == "Administrator" or set(ALLOWED_ROLES) & set(frappe.get_roles(user)):
		return
	frappe.throw(
		_("You are not permitted to view the Intercompany Salary Cost Allocation report."),
		frappe.PermissionError,
	)
