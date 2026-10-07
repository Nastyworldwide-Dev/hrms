# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RosterDay(Document):
	"""One person's Day Type for one date, with no shift attached.

	The name is "{employee}-{date}", so the primary key allows one marker per
	person per day. hrms.utils.ot_calculation._read_rostered_day_types reads it
	before any Shift Assignment; hrms.api.roster.set_day_type writes it.
	"""
