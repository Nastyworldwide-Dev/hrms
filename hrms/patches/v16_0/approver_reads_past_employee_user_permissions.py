"""A superior named as approver can open the request they are asked to decide.

REPORTED 21 Sep 2026: "Superior cannot approve on duty application, this
approver cant approve still persist". Two earlier fixes were validation-layer,
so the symptom survived them. The real refusal was a READ, before any decision
gate ran.

Attendance Request, OT Request and Replacement Leave Claim carry no approver
field of their own, and their `employee` link carried no `ignore_user_permissions`
flag — unlike Leave Application, Expense Claim and Shift Request, where it has
always been set. So an `allow=Employee` User Permission (which this fork mints
per person) fenced an approver to their OWN employee id on exactly these three
doctypes: `frappe.has_permission` answered False, the PWA rendered no Approve
button, the Team queue came back empty, and `decide()` threw PermissionError.

The doctype JSON now sets the flag. A live site can silently ignore that: a
Property Setter for `ignore_user_permissions` on the field outranks the
reloaded JSON, and Customize Form writes one whenever anyone touches the field.
So the flag is also written directly to the stored DocField, and any Property
Setter holding it off is logged and removed.

The system checks itself — no console step, nothing for HR to run. A site that
is already correct is untouched. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

DOCTYPES = ("Attendance Request", "OT Request", "Replacement Leave Claim")
FIELD = "employee"
PROPERTY = "ignore_user_permissions"


def execute():
	fixed = 0
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			logger.info("[approver_reads] %s not installed on this site", doctype)
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
				"[approver_reads] removing Property Setter %s on %s.%s (value=%r, set by %s on %s) — it "
				"kept the field fenced by User Permissions, so a named approver could not open the request",
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
			logger.warning("[approver_reads] %s has no %s field", doctype, FIELD)
			continue
		if not field.get(PROPERTY):
			frappe.db.set_value("DocField", field.name, PROPERTY, 1, update_modified=False)
			fixed += 1
			logger.info("[approver_reads] %s.%s now ignores User Permissions", doctype, FIELD)

		if overrides or not field.get(PROPERTY):
			frappe.clear_cache(doctype=doctype)

	logger.info("[approver_reads] %d of %d doctype(s) needed the flag", fixed, len(DOCTYPES))
