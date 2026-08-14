"""Contact-directory API used by the /hrms PWA.

Public endpoints:
    hrms.api.hr_contacts.get_reporting_manager(employee=None)
    hrms.api.hr_contacts.list_hr_contacts()

Both return a uniform contact-card shape so the front-end can render
them with the same component.
"""

from __future__ import annotations

import logging

import frappe

from hrms.utils.identity import get_employee

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
	return get_employee()


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
	"""Return curated active HR contacts from the HR Contact doctype.

	A row appears only if ALL of the following hold:
	- HR Contact.is_active = 1
	- Employee.status = 'Active'
	- The linked User still has HR Manager or HR User role
	  (so revoking the role hides the contact automatically, no re-save needed)

	Ordered by HR Contact.display_order ASC, then employee ID ASC.
	"""
	rows = frappe.db.sql(
		"""
		SELECT
			e.name AS name,
			e.employee_name,
			e.designation,
			e.company_email,
			e.prefered_email,
			e.personal_email,
			e.cell_number,
			e.image,
			e.user_id,
			hc.display_order
		FROM `tabHR Contact` hc
		INNER JOIN `tabEmployee` e
			ON e.name = hc.employee
		INNER JOIN `tabHas Role` r
			ON r.parent = e.user_id
		   AND r.parenttype = 'User'
		   AND r.role IN %(roles)s
		WHERE hc.is_active = 1
		  AND e.status = 'Active'
		GROUP BY e.name, hc.display_order
		ORDER BY hc.display_order ASC, e.name ASC
		""",
		{"roles": HR_ROLES},
		as_dict=True,
	)
	cards = [_to_contact_card(r) for r in rows if r]
	logger.info("[hr_contacts] list_hr_contacts -> %d (role-checked)", len(cards))
	return cards


@frappe.whitelist()
def employee_with_hr_role_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | None = None,
):
	"""Link-field query used by the HR Contact form to limit the Employee
	picker to active Employees whose linked User has an HR role.
	"""
	logger.info(
		"[hr_contacts] picker query txt=%r start=%s page_len=%s",
		txt,
		start,
		page_len,
	)
	return frappe.db.sql(
		"""
		SELECT e.name, e.employee_name, e.designation
		FROM `tabEmployee` e
		INNER JOIN `tabHas Role` r
			ON r.parent = e.user_id
		   AND r.parenttype = 'User'
		   AND r.role IN %(roles)s
		WHERE e.status = 'Active'
		  AND (e.name LIKE %(txt)s OR e.employee_name LIKE %(txt)s)
		GROUP BY e.name
		ORDER BY e.employee_name
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"roles": HR_ROLES,
			"txt": f"%{txt or ''}%",
			"start": int(start) if start else 0,
			"page_len": int(page_len) if page_len else 20,
		},
	)
