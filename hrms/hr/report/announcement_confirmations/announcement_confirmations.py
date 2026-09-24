"""Announcement Confirmations — script report (alpha.7 4.6; owner Q6, 25 Sep).

One row per person the notice is addressed to: read or not, confirmed the
CURRENT wording or not, and when. HR chases from it and exports it. Fenced to
the caller's companies (report_scope.fenced_companies), applied inside the
query. Nothing here writes.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _

from hrms.utils.report_scope import fenced_companies

logger = logging.getLogger(__name__)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.announcement:
		return _columns(), []
	doc = frappe.get_doc("HR Announcement", filters.announcement)
	from hrms.api.announcements import _audience_employees

	companies = fenced_companies()
	audience = _audience_employees(doc)
	people_filters = {"name": ("in", audience or [""])}
	if companies:
		people_filters["company"] = ("in", companies)
	people = frappe.get_all(
		"Employee",
		filters=people_filters,
		fields=["name", "employee_name", "company", "department"],
		order_by="employee_name asc",
	)
	reads = {
		r.employee: r
		for r in frappe.get_all(
			"HR Announcement Read",
			filters={"announcement": doc.name},
			fields=["employee", "read_on", "acknowledged", "acknowledged_on", "acknowledged_version"],
		)
	}
	version = doc.version or 1
	rows = []
	for p in people:
		r = reads.get(p.name)
		confirmed = bool(r and r.acknowledged and (r.acknowledged_version or 1) >= version)
		if filters.show == "Confirmed" and not confirmed:
			continue
		if filters.show == "Not confirmed" and confirmed:
			continue
		rows.append(
			{
				"employee": p.name,
				"employee_name": p.employee_name,
				"company": p.company,
				"department": p.department,
				"read_on": r.read_on if r else None,
				"confirmed": _("Yes")
				if confirmed
				else (_("Not needed") if not doc.acknowledge_required else _("No")),
				"confirmed_on": r.acknowledged_on if confirmed else None,
			}
		)
	logger.info(
		"[announcement_confirmations] %s fence=%s audience=%d rows=%d",
		doc.name,
		companies or "none",
		len(people),
		len(rows),
	)
	return _columns(), rows


def _columns() -> list[dict]:
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Name"), "fieldtype": "Data", "width": 200},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{"fieldname": "read_on", "label": _("Opened"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "confirmed", "label": _("Confirmed"), "fieldtype": "Data", "width": 110},
		{"fieldname": "confirmed_on", "label": _("Confirmed on"), "fieldtype": "Datetime", "width": 160},
	]
