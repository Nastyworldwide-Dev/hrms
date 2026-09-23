"""Staff Without A Shift — script report (23 Sep 2026).

Owner ruling: staff check in as normal on any day, and rest days and public
holidays are overtime. That needs a shift to know the day's calendar; a punch
from someone with none is stored off-shift and never reaches overtime. The
system does not invent a rate, so HR sees who is missing one here and sets an
assignment or a default shift on the Employee.

HR Manager and System Manager only; fenced to the caller's companies
(`hrms.utils.report_scope.fenced_companies`). An empty report is healthy.
Nothing here writes.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import today

from hrms.utils.report_scope import fenced_companies

logger = logging.getLogger(__name__)

WHY = _(
	"No shift set up: overtime on rest days and public holidays cannot be counted "
	"until HR sets a shift assignment or a default shift."
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	companies = fenced_companies(filters.get("company"))
	on = today()
	employee_filters = {"status": "Active"}
	if companies:
		employee_filters["company"] = ("in", companies)
	people = frappe.get_all(
		"Employee",
		filters=employee_filters,
		fields=["name", "employee_name", "company", "department", "default_shift"],
		order_by="company asc, employee_name asc",
	)
	assigned = {
		row.employee
		for row in frappe.get_all(
			"Shift Assignment",
			filters={"status": "Active", "docstatus": 1, "start_date": ["<=", on]},
			or_filters=[["end_date", ">=", on], ["end_date", "is", "not set"]],
			fields=["employee"],
		)
	}
	rows = [
		{
			"employee": person.name,
			"employee_name": person.employee_name,
			"company": person.company,
			"department": _department(person.department),
			"why": WHY,
		}
		for person in people
		if not person.default_shift and person.name not in assigned
	]
	logger.info(
		"[staff_without_a_shift] fence=%s active=%d without_shift=%d",
		companies or "none",
		len(people),
		len(rows),
	)
	return _columns(), rows


def _department(name: str | None) -> str:
	"""The name people use: ERPNext appends " - <company abbr>" to the record."""
	if not name:
		return ""
	head, sep, tail = name.rpartition(" - ")
	return head if sep and tail and " " not in tail else name


def _columns() -> list[dict]:
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 200},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{"fieldname": "department", "label": _("Department"), "fieldtype": "Data", "width": 150},
		{"fieldname": "why", "label": _("Why"), "fieldtype": "Small Text", "width": 500},
	]
