# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

from hrms.hr.utils import set_geolocation_from_coordinates
from hrms.utils.coordinates import WGS84, to_wgs84

logger = logging.getLogger(__name__)


class ShiftLocation(Document):
	def validate(self):
		self.convert_coordinates()
		self.set_geolocation()
		self.validate_shift_rules()

	def convert_coordinates(self):
		"""A pin copied from a Chinese map is stored as the phones will see it.

		Maps inside mainland China publish GCJ-02 or BD-09 positions, 100 to
		700 m from WGS-84. HR says which map the pin came from; the row keeps
		WGS-84 only, so the fence and the phones agree.
		"""
		system = getattr(self, "coordinate_system", None) or WGS84
		if system == WGS84 or self.latitude is None or self.longitude is None:
			return
		before = (self.latitude, self.longitude)
		try:
			self.latitude, self.longitude = to_wgs84(self.latitude, self.longitude, system)
		except ValueError as e:
			frappe.throw(_("Coordinates Read From: {0}").format(e))
		self.coordinate_system = WGS84
		logger.info(
			"[shift_location] %s pin converted from %s to WGS-84: %s -> %s",
			self.name,
			system,
			before,
			(self.latitude, self.longitude),
		)

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
