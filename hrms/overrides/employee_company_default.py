"""A request's company is the Employee's company — the server decides, not the form.

15 September 2026: an employee filing a Shift Request in Nadi got "Value
missing for Shift Request: Company". The PWA create form hides company (it is
not the employee's choice) and sends nothing for it, so the value came from
the session's user default Company — right by luck, blank for a user without
one. Every sibling request doctype (Leave Application, Attendance Request,
OT Request, Replacement Leave Claim, Employee Advance, Expense Claim, Shift
Assignment) carries `fetch_from: employee.company`, which Frappe applies in
`_validate_links` before the mandatory check; Shift Request never had it.

One rule for every request that names an employee: the company is the
Employee's company. Called from the controller's `validate` (or wired as a
`doc_events` validate hook) — both run before `_validate_mandatory`.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def set_company_from_employee(doc, method=None):
	"""Set `doc.company` to the Employee's company; a client value never wins."""
	employee = doc.get("employee")
	if not employee:
		return
	company = frappe.db.get_value("Employee", employee, "company")
	if not company or doc.get("company") == company:
		return
	logger.info(
		"[company_default] %s for %s: company %r -> %r",
		doc.doctype,
		employee,
		doc.get("company"),
		company,
	)
	doc.company = company
