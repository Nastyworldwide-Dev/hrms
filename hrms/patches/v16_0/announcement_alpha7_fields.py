"""alpha.7 announcement fields: Summary, Cover image, Urgent, Notify on
publish, version, and public pasted images (owner, 25 Sep: Q7 yes).

The JSON carries the fields and `make_attachments_public`; this makes sure a
site gets them even when its sync stops early (the reason
install_announcement_doctypes exists), and clears a Property Setter that
would keep pasted images private (a site row outranks the JSON). Existing
notices get their Summary from their body's opening words, so no Home card
or push goes out empty. Files already uploaded are NOT made public: that is
historical data and needs the owner's word. Idempotent; nobody runs anything.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	for doctype in ("hr_announcement", "hr_announcement_read"):
		frappe.reload_doc("hr", "doctype", doctype)

	shadows = frappe.get_all(
		"Property Setter",
		filters={"doc_type": "HR Announcement", "property": "make_attachments_public"},
		fields=["name", "value", "owner", "modified"],
	)
	for row in shadows:
		logger.warning(
			"[announcements] removing Property Setter %s (make_attachments_public=%r, by %s on %s): "
			"it kept pasted images private, so staff saw broken pictures",
			row.name,
			row.value,
			row.owner,
			row.modified,
		)
		frappe.delete_doc("Property Setter", row.name)
	if shadows:
		frappe.clear_cache(doctype="HR Announcement")

	from hrms.hr.doctype.hr_announcement.hr_announcement import summary_from

	filled = 0
	for row in frappe.get_all(
		"HR Announcement", filters={"summary": ("in", ("", None))}, fields=["name", "body"]
	):
		frappe.db.set_value(
			"HR Announcement", row.name, "summary", summary_from(row.body), update_modified=False
		)
		filled += 1
	frappe.db.sql("update `tabHR Announcement` set version = 1 where ifnull(version, 0) = 0")
	logger.info("[announcements] alpha.7 fields ready; summaries filled: %d", filled)
