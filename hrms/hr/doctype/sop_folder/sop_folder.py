# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class SOPFolder(Document):
	def on_trash(self):
		"""A folder that still holds SOPs cannot go: its SOPs would point at a
		name that no longer exists and vanish from the staff page. Counts the
		table, not a permission-fenced list, so an HR user fenced to one company
		cannot delete a folder that holds another company's SOP."""
		held = frappe.db.count("SOP Document", {"folder": self.name})
		if held:
			logger.info("[sop_folder] refusing to delete %s: %d SOP(s) inside", self.name, held)
			frappe.throw(_("Move its SOPs first. {0} SOP(s) are in this folder.").format(held))
