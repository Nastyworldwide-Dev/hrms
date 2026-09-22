# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class HRAnnouncementRead(Document):
	"""One row per employee per announcement. Written by the PWA when a card is
	opened, and again when it is acknowledged.

	Deliberately NOT a child table of the announcement: a child table is
	rewritten wholesale on every parent save, so an HR edit to the wording
	would drop every read record. It is also the wrong shape for the only
	question anyone asks of it — "has this person read it" — which is a lookup
	by two keys.
	"""

	def validate(self):
		self.enforce_one_row()

	def enforce_one_row(self):
		"""Reading twice is not two readings. Without this an employee who
		opens a card on their phone and again on a laptop counts twice, and
		"read by 31 of 44" becomes a number nobody can trust."""
		existing = frappe.db.exists(
			"HR Announcement Read",
			{
				"announcement": self.announcement,
				"employee": self.employee,
				"name": ("!=", self.name or ""),
			},
		)
		if existing:
			frappe.throw(
				_("This announcement is already marked as read for {0}.").format(self.employee),
				frappe.DuplicateEntryError,
			)
