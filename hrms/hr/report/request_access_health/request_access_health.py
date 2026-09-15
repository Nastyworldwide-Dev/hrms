"""Request Access Health — script report (15 Sep 2026).

Owner's rule: we never ask an employee to run a diagnostic; the system finds
it itself. One row per (user, request doctype) that user may NOT create for
their own employee, probed the way Nadi's form files it — as that user, own
employee set, no company, no posting date — with the gate that refused
(`hrms.api.diagnose`) and a plain sentence. An empty report is the healthy
state. Nothing here writes.

HR Manager and System Manager only; fenced to the caller's companies the way
the other HR reports are (`hrms.utils.report_scope.fenced_companies`), and a
fenced caller asking for another company is refused, not shown an empty page.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _

from hrms.utils.report_scope import fenced_companies
from hrms.utils.request_access import PWA_REQUEST_DOCTYPES, scan

logger = logging.getLogger(__name__)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	companies = fenced_companies(filters.get("company"))
	doctypes = (filters.doctype,) if filters.get("doctype") else PWA_REQUEST_DOCTYPES
	logger.info("[request_access_health] execute fence=%s doctypes=%d", companies or "none", len(doctypes))
	rows = scan(companies or None, doctypes)
	return _columns(), rows


def _columns() -> list[dict]:
	return [
		{"fieldname": "user", "label": _("User"), "fieldtype": "Link", "options": "User", "width": 220},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 130,
		},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 180},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{"fieldname": "doctype", "label": _("Request Type"), "fieldtype": "Data", "width": 190},
		{"fieldname": "refused_by", "label": _("Refused By"), "fieldtype": "Data", "width": 200},
		{"fieldname": "why", "label": _("Why"), "fieldtype": "Small Text", "width": 500},
	]
