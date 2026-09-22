# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate

logger = logging.getLogger(__name__)

#: The doctype each audience names, used to CHECK that the value HR typed is a
#: real record. Not a Dynamic Link: Frappe resolves a Dynamic Link's target
#: during _validate_links(), which runs before every controller hook, so a
#: target derived from `audience` can never be populated in time. Verified on
#: the bench rather than reasoned about — the first two attempts (validate,
#: then before_validate) both threw "Audience DocType must be set first".
AUDIENCE_DOCTYPE = {
	"Company": "Company",
	"Department": "Department",
	"Branch": "Branch",
}

#: Two weeks. An announcement with no end date is a noticeboard that rots:
#: somebody has to remember to take it down, and nobody ever does. HR can
#: change it, but they never have to think about it.
DEFAULT_RUN_DAYS = 14


class HRAnnouncement(Document):
	def validate(self):
		self.set_defaults()
		self.resolve_audience()
		self.validate_dates()
		self.enforce_single_pin()

	def set_defaults(self):
		"""HR types a title and a body; everything else has a right answer."""
		if not self.publish_from:
			self.publish_from = nowdate()
		if not self.publish_until:
			self.publish_until = add_days(self.publish_from, DEFAULT_RUN_DAYS)

	def resolve_audience(self):
		"""Everyone means everyone — the link is cleared rather than left
		holding whatever was picked before the audience changed, which would
		silently narrow a company-wide notice to one department."""
		if self.audience == "Everyone":
			self.audience_value = None
			return
		doctype = AUDIENCE_DOCTYPE.get(self.audience)
		if not doctype:
			frappe.throw(_("{0} is not an audience this app knows.").format(self.audience))
		if not self.audience_value:
			frappe.throw(_("Choose which {0} this is for.").format(self.audience.lower()))
		# The value is a typed name rather than a validated Link, so the check
		# is ours. Without it a typo publishes an announcement addressed to a
		# department that does not exist — which shows it to nobody, silently,
		# and HR has no way to tell that from "nobody has read it yet".
		if not frappe.db.exists(doctype, self.audience_value):
			frappe.throw(
				_("There is no {0} called {1}.").format(self.audience.lower(), self.audience_value)
			)

	def validate_dates(self):
		if getdate(self.publish_until) < getdate(self.publish_from):
			frappe.throw(_("An announcement cannot stop showing before it starts."))

	def enforce_single_pin(self):
		"""One pin. Two pinned announcements are two things claiming to be the
		most important, which is the same as none — and the PWA gives the pin a
		fixed slot, so a second would displace the first with no way to tell
		which won."""
		if not self.pinned:
			return
		others = frappe.get_all(
			"HR Announcement",
			filters={"pinned": 1, "name": ("!=", self.name or "")},
			pluck="name",
		)
		if others:
			logger.info("[announcement] unpinning %s for %s", others, self.name)
			for name in others:
				# db_set, not a save: unpinning is a consequence of THIS edit and
				# must not re-run another document's validate — which would, among
				# other things, re-enforce this same rule and recurse.
				frappe.db.set_value("HR Announcement", name, "pinned", 0, update_modified=False)

	def on_trash(self):
		"""The read rows are about a thing that no longer exists. Left behind
		they become an unreadable audit trail — a name, a date and a dangling
		link."""
		deleted = frappe.db.delete("HR Announcement Read", {"announcement": self.name})
		logger.info("[announcement] %s deleted, read rows removed: %s", self.name, deleted)
