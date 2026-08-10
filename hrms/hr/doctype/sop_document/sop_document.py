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

	def on_update(self):
		self.cleanup_replaced_attachment()

	def cleanup_replaced_attachment(self):
		"""'Remove attachment' only clears the field — the attached File row
		would survive, and the API's File-row fallback would resurrect it on
		the next read. Deleting the cleared/replaced row makes removal real
		(and stops orphaned File rows accumulating on every replace)."""
		before = self.get_doc_before_save()
		old = before.get("attachment") if before else None
		if not old or old == self.attachment:
			return
		file_names = frappe.get_all(
			"File",
			filters={
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"file_url": old,
			},
			pluck="name",
		)
		for file_name in file_names:
			# the actor already held write on this SOP for the save itself; the
			# File cleanup is a cascade of that edit, not a separate privilege
			frappe.delete_doc("File", file_name, ignore_permissions=True)
		logger.info(
			"[sop_document] %s: removed %d file row(s) for replaced attachment %s",
			self.name,
			len(file_names),
			old,
		)

	def validate_scope(self):
		"""Scope and department must agree: a Department SOP is meaningless
		without a department, and a stale department on a General SOP would
		silently narrow nothing while confusing the row-scope predicate."""
		if self.scope == "Department":
			if not self.department:
				frappe.throw(_("Department is required when Scope is Department."))
			# Department is a nested-set tree and the row scope matches on exact
			# equality — a group department has no direct members, so such an SOP
			# would publish to nobody at all.
			if frappe.db.get_value("Department", self.department, "is_group"):
				logger.info(
					"[sop_document] %s: rejecting group department %s",
					self.name,
					self.department,
				)
				frappe.throw(
					_("Select a specific (non-group) department — group departments have no direct members.")
				)
		elif self.department:
			logger.info(
				"[sop_document] %s: clearing department %s on General scope",
				self.name,
				self.department,
			)
			self.department = None
