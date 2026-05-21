"""Contact-directory API used by the /hrms PWA.

Public endpoints:
    nsty.api.hr_contacts.get_reporting_manager(employee=None)
    nsty.api.hr_contacts.list_hr_contacts()

Both return a uniform contact-card shape so the front-end can render
them with the same component.
"""

from __future__ import annotations

import logging

import frappe

logger = logging.getLogger(__name__)

HR_ROLES = ("HR Manager", "HR User")
_CONTACT_FIELDS = [
	"name",
	"employee_name",
	"designation",
	"company_email",
	"prefered_email",
	"personal_email",
	"cell_number",
	"image",
	"user_id",
]


def _to_contact_card(row: dict) -> dict:
	if not row:
		return None
	email = row.get("company_email") or row.get("prefered_email") or row.get("personal_email")
	return {
		"name": row.get("name"),
		"employee_name": row.get("employee_name") or "",
		"designation": row.get("designation") or "",
		"email": email or "",
		"phone": row.get("cell_number") or "",
		"image": row.get("image") or "",
	}


def _current_employee() -> str | None:
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	return employee


@frappe.whitelist()
def get_reporting_manager(employee: str | None = None) -> dict | None:
	"""Return the reporting manager's contact card for `employee`.

	`employee` defaults to the Employee linked to the current session user.
	Returns None if there is no reports_to or no resolvable manager.
	"""
	employee = employee or _current_employee()
	if not employee:
		return None

	reports_to = frappe.db.get_value("Employee", employee, "reports_to")
	if not reports_to:
		return None

	row = frappe.db.get_value(
		"Employee",
		reports_to,
		_CONTACT_FIELDS,
		as_dict=True,
	)
	card = _to_contact_card(row)
	logger.info(
		"[hr_contacts] reporting_manager employee=%s -> %s",
		employee,
		card and card["name"],
	)
	return card


@frappe.whitelist()
def list_hr_contacts() -> list[dict]:
	"""Return all active employees whose linked User has an HR role."""
	hr_users = frappe.get_all(
		"Has Role",
		filters={
			"role": ["in", HR_ROLES],
			"parenttype": "User",
		},
		pluck="parent",
	)
	if not hr_users:
		return []

	rows = frappe.get_all(
		"Employee",
		filters={
			"user_id": ["in", list(set(hr_users))],
			"status": "Active",
		},
		fields=_CONTACT_FIELDS,
		order_by="employee_name asc",
	)
	cards = [_to_contact_card(r) for r in rows if r]
	logger.info("[hr_contacts] list_hr_contacts -> %d", len(cards))
	return cards
