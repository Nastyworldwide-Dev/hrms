"""Install the announcement board's doctypes (v16_0).

22 September 2026. A new DocType ships as JSON and is normally created when
the site syncs the app's doctype folders — but a site whose sync fails PART
WAY leaves the rest of the app uninstalled, and this bench already carries a
Shift Assignment permission-level error that stops it before it reaches the
new folders. The board would then be a feature whose endpoints exist and whose
tables do not: every call a 500, on Home, for everybody.

So the two doctypes are imported explicitly and idempotently.
`import_file_by_path` is the same function the sync itself uses; running it
again on an installed doctype is a no-op beyond a re-sync, which is why this
is safe to re-run and safe either side of the sync reaching the same files.

reset_permissions is deliberately FALSE. The permission rows are part of the
JSON on first install; forcing them on every run would wipe any grant a site
has since made in Desk — and "HR added a role and the next release removed it"
is a defect class this app has already paid for.
"""

import logging
import os

import frappe
from frappe.modules.import_file import import_file_by_path

logger = logging.getLogger(__name__)

DOCTYPES = ("hr_announcement", "hr_announcement_read")


def execute():
	base = frappe.get_app_path("hrms", "hr", "doctype")
	for folder in DOCTYPES:
		path = os.path.join(base, folder, f"{folder}.json")
		if not os.path.exists(path):
			# The app arrived without the file. Louder than a silent skip, but
			# not fatal: a raising patch blocks every later one.
			logger.error("[announcements] %s is missing; the board will not work", path)
			continue
		import_file_by_path(path, force=False, reset_permissions=False)
		logger.info("[announcements] ensured %s", folder)

	frappe.db.commit()
	for doctype in ("HR Announcement", "HR Announcement Read"):
		if not frappe.db.exists("DocType", doctype):
			logger.error("[announcements] %s did not install", doctype)
