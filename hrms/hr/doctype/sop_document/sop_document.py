# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class SOPDocument(Document):
	def validate(self):
		self.validate_scope()

	def validate_scope(self):
		"""Scope and department must agree: a Department SOP is meaningless
		without a department, and a stale department on a General SOP would
		silently narrow nothing while confusing the row-scope predicate."""
		if self.scope == "Department":
			if not self.department:
				frappe.throw(_("Department is required when Scope is Department."))
		elif self.department:
			logger.info(
				"[sop_document] %s: clearing department %s on General scope",
				self.name,
				self.department,
			)
			self.department = None
