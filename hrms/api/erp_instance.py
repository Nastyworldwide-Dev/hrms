"""Resolve which ERPNext instance a staff member's ops work lives on.

HR runs centrally on this site, but each company keeps its own ERPNext for
finance/ops. The PWA shows an "Open my ERP" button that deep-links the employee
to their own company's instance.

Convenience only — this never gates anything. Attendance does not affect whether
a staff member can reach their ERP.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: Everything this API is allowed to hand to a staff member. The
#: `HRMS ERP Instance` doctype also carries the shadow-sync credentials
#: (`api_key` / `api_secret`, both permlevel 1); this allow-list — not the
#: permlevel — is what keeps them out of the PWA payload, because these reads
#: go through `frappe.db` and bypass permlevel filtering entirely.
PUBLIC_INSTANCE_FIELDS = ("instance_name", "url")


def get_instance_for_company(company: str) -> dict | None:
	"""The enabled instance serving `company`, or None when unmapped."""
	if not company:
		return None

	rows = frappe.get_all(
		"HRMS ERP Instance Company",
		filters={"company": company},
		fields=["parent"],
		limit=1,
	)
	if not rows:
		logger.debug("[erp_instance] no instance mapped for company %s", company)
		return None

	instance = frappe.db.get_value(
		"HRMS ERP Instance",
		{"name": rows[0].parent, "enabled": 1},
		list(PUBLIC_INSTANCE_FIELDS),
		as_dict=True,
	)
	if not instance:
		logger.info("[erp_instance] instance for company %s exists but is disabled", company)
		return None

	return {field: instance.get(field) for field in PUBLIC_INSTANCE_FIELDS}


@frappe.whitelist()
def get_my_erp_instance() -> dict | None:
	"""The ERP instance for the logged-in user's own employee record.

	Self-scoped by construction: the employee is derived from the session, never
	taken from the caller, so this cannot be used to probe another company.
	"""
	company = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		"company",
	)
	if not company:
		logger.debug("[erp_instance] no active employee for user %s", frappe.session.user)
		return None

	return get_instance_for_company(company)
