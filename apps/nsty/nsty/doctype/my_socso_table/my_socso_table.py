# Copyright (c) 2026, Nsty and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MySOCSOTable(Document):
	def validate(self):
		if self.wage_from is None or self.wage_to is None:
			frappe.throw("Wage From and Wage To are required.")
		if self.wage_to < self.wage_from:
			frappe.throw("Wage To must be greater than or equal to Wage From.")
