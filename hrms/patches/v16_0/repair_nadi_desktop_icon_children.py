"""Put the nine HR workspaces back under the Nadi app icon.

Frappe decides whether an app icon opens a workspace modal or navigates on one
condition (`frappe/desk/page/desktop/desktop.js:1123`):

    if (this.child_icons?.length && (icon_type == "App" || icon_type == "Folder"))

`child_icons` is assembled by matching each icon's `parent_icon` against the
parent's label (`desktop.js:204`). On live sites that match was broken twice
over:

1. The rebrand changed `parent_icon` "Frappe HR" -> "Nadi" in the nine child
   fixtures without advancing their `modified`, so Frappe's timestamp gate
   (`frappe/modules/import_file.py:141`) skipped the import and the rows kept
   the old label.
2. `rename_frappe_hr_desktop_icon` then found "Nadi" already created by
   `sync_all` and took its other branch — `delete_doc(..., force=True)` —
   removing the very record those nine rows still pointed at. `force=True`
   skips the link check that would have refused.

The result is an App icon with zero children, which degrades to a plain link.

**The fixture timestamps are the primary fix**; `sync_all` runs before
post_model_sync patches, so on most sites the children are already repointed by
the time this runs and it finds nothing to do. This is the backstop for what
fixtures cannot reach: a row whose `modified` is newer than the fixture because
someone edited it in Desk, and the orphaned "Frappe HR" record itself, which no
fixture can delete.

Order is the whole defect, so it is the whole fix: **repoint, then delete.**
Idempotent, and a site that never carried the old label is left alone rather
than half-repaired.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

OLD_LABEL = "Frappe HR"
NEW_LABEL = "Nadi"


def execute():
	if not frappe.db.exists("Desktop Icon", NEW_LABEL):
		logger.info("[repair_nadi_icon] no %r icon on this site — nothing to repair onto", NEW_LABEL)
		return

	orphans = frappe.get_all("Desktop Icon", filters={"parent_icon": OLD_LABEL}, pluck="name")

	# Repoint FIRST. Deleting the parent while children still name it is the
	# bug this patch exists to undo; doing it in that order again would simply
	# re-strand them.
	for name in orphans:
		frappe.db.set_value("Desktop Icon", name, "parent_icon", NEW_LABEL, update_modified=False)
	if orphans:
		logger.info("[repair_nadi_icon] repointed %d icon(s) to %r: %s", len(orphans), NEW_LABEL, orphans)

	if frappe.db.exists("Desktop Icon", OLD_LABEL):
		frappe.delete_doc("Desktop Icon", OLD_LABEL, ignore_permissions=True, force=True)
		logger.info("[repair_nadi_icon] removed the orphaned %r icon", OLD_LABEL)

	if orphans:
		# boot caches desktop_icons; without this the launcher stays empty until
		# the next cache bust, which on a live site can be a long time.
		frappe.clear_cache()
