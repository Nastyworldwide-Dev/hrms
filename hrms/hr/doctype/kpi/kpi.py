# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class KPI(Document):
	def validate(self):
		self.validate_unique_kpi()

	def validate_unique_kpi(self):
		existing = frappe.db.exists(
			"KPI",
			{"title": self.title, "kra": self.kra, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				_("A KPI with title {0} already exists for KRA {1}").format(
					frappe.bold(self.title), frappe.bold(self.kra)
				),
				exc=frappe.DuplicateEntryError,
			)
