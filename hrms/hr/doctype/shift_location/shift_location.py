# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from hrms.hr.utils import set_geolocation_from_coordinates


class ShiftLocation(Document):
	def validate(self):
		self.set_geolocation()
		self.validate_shift_rules()

	def validate_shift_rules(self):
		# duplicate department rows (or two blank defaults) would resolve by
		# arbitrary row order, so reject them outright
		seen = {}
		for row in self.shift_rules:
			key = row.department or ""
			if key in seen:
				label = row.department or _("(blank — site default)")
				frappe.throw(
					_("Row #{0}: duplicate Shift Rule for department {1} (see row #{2})").format(
						row.idx, frappe.bold(label), seen[key]
					),
					title=_("Duplicate Shift Rule"),
				)
			seen[key] = row.idx

	@frappe.whitelist()
	def set_geolocation(self):
		set_geolocation_from_coordinates(self)
