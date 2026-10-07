"""A named approver in another company can open the request they are asked to decide.

REPORTED 7 Oct 2026 (HR): "make the approval list show everything where the user is the named
approver, regardless of company. Amran won't be the last cross-entity manager (Dubai, South
Africa)." Amran sits in TNME; his reports sit in other companies and name him as their approver;
he saw none of their requests in Nadi.

Four layers said no on a company. Three are code. The fourth is Frappe's own User Permission
check: the `company` Link on Leave Application, Expense Claim, Shift Request, Attendance Request,
OT Request and Replacement Leave Claim carried no `ignore_user_permissions`, so an approver holding
an `allow=Company` User Permission for his own company got `frappe.has_permission` False on a
report's request in another company (Leave Application passed only through a DocShare).

The doctype JSON now sets the flag. A live site can silently ignore that: a Property Setter for
`ignore_user_permissions` on the field outranks the reloaded JSON, and Customize Form writes one
whenever anyone touches the field. So the flag is also written directly to the stored DocField,
and any Property Setter holding it off is logged and removed — same shape as
approver_reads_past_employee_user_permissions, for the `company` field.

The Company User Permission was also HR's company fence on these six doctypes. It is restated in
code (hrms.overrides.approval_row_scope, ot_row_scope), so a company-fenced HR user stays fenced
for the requests they see only because they are HR.

The system checks itself — no console step, nothing for HR to run. A site that is already
correct is untouched. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

DOCTYPES = (
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"Attendance Request",
	"OT Request",
	"Replacement Leave Claim",
)
FIELD = "company"
PROPERTY = "ignore_user_permissions"


def execute():
	fixed = 0
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			logger.info("[approver_reads_company] %s not installed on this site", doctype)
			continue

		# A Property Setter outranks the JSON. Log what is removed — value, who
		# set it and when — so a site that did it on purpose can read it back.
		overrides = frappe.db.get_all(
			"Property Setter",
			filters={
				"doc_type": doctype,
				"field_name": FIELD,
				"property": PROPERTY,
				"doctype_or_field": "DocField",
			},
			fields=["name", "value", "owner", "modified"],
		)
		for row in overrides:
			logger.warning(
				"[approver_reads_company] removing Property Setter %s on %s.%s (value=%r, set by %s on %s) — "
				"it kept the field fenced by User Permissions, so a named approver in another company "
				"could not open the request",
				row.name,
				doctype,
				FIELD,
				row.value,
				row.owner,
				row.modified,
			)
			frappe.delete_doc("Property Setter", row.name)

		field = frappe.db.get_value(
			"DocField", {"parent": doctype, "fieldname": FIELD}, ["name", PROPERTY], as_dict=True
		)
		if not field:
			logger.warning("[approver_reads_company] %s has no %s field", doctype, FIELD)
			continue
		if not field.get(PROPERTY):
			frappe.db.set_value("DocField", field.name, PROPERTY, 1, update_modified=False)
			fixed += 1
			logger.info("[approver_reads_company] %s.%s now ignores User Permissions", doctype, FIELD)

		if overrides or not field.get(PROPERTY):
			frappe.clear_cache(doctype=doctype)

	logger.info("[approver_reads_company] %d of %d doctype(s) needed the flag", fixed, len(DOCTYPES))
