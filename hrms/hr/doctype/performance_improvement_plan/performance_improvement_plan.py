# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PerformanceImprovementPlan(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if self.pip_start_date and self.pip_end_date:
			if self.pip_end_date <= self.pip_start_date:
				frappe.throw(
					_("PIP End Date must be after Start Date"),
					title=_("Invalid Dates"),
				)
