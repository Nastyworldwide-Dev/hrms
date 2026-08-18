# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.document import Document


class HRMSSchemaGapRuling(Document):
	def validate(self):
		# A ruling is an accountable decision: stamp who made it. Overwritten on
		# every edit on purpose — the last editor owns the current ruling.
		self.ruled_by = frappe.session.user
