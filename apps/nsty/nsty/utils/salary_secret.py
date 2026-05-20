"""Salary secrecy gate — treat salary like an API-key secret.

Public API:
    get_salary_secret(employee) -> float
    mask_salary(value) -> str

Access policy (deny-by-default):
  - Administrator (user == "Administrator") is ALWAYS denied, regardless of role.
  - Users with the "HR Manager" role are allowed.
  - The employee themselves (Employee.user_id == current user) is allowed
    to see their own salary.
  - Everyone else is denied with frappe.PermissionError.

The amount is stored on Salary Structure Assignment.base, which is the
canonical "basic" used elsewhere in this app.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

HR_ROLE = "HR Manager"
MASK = "********"


def mask_salary(value: float | int | None) -> str:
	"""Render salary as an API-key-style mask (used for UI/list views)."""
	if value is None:
		return MASK
	return MASK


def _is_self(employee: str, user: str) -> bool:
	if not employee or not user:
		return False
	owner = frappe.db.get_value("Employee", employee, "user_id")
	return bool(owner) and owner == user


def _can_view_salary(employee: str) -> bool:
	user = frappe.session.user

	if user == "Administrator":
		logger.warning(
			"[salary_secret] Administrator blocked from salary view employee=%s",
			employee,
		)
		return False

	if HR_ROLE in frappe.get_roles(user):
		return True

	if _is_self(employee, user):
		return True

	return False


@frappe.whitelist()
def get_salary_secret(employee: str) -> float:
	"""Return the employee's basic salary if the caller is authorised.

	Raises frappe.PermissionError otherwise. Result is logged with the
	accessing user for audit.
	"""
	if not employee:
		frappe.throw(_("Employee is required."))

	if not _can_view_salary(employee):
		logger.warning(
			"[salary_secret] DENY user=%s employee=%s",
			frappe.session.user,
			employee,
		)
		raise frappe.PermissionError(_("Salary information is restricted. Contact HR if you need access."))

	assignment = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1},
		["base"],
		order_by="from_date desc",
	)
	base = float(assignment or 0.0)
	logger.info(
		"[salary_secret] ALLOW user=%s employee=%s",
		frappe.session.user,
		employee,
	)
	return base
