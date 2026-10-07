# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

#: A day with no shift may be marked only as a day off (owner, 7 Oct 2026): never
#: Work Day, which stays a Day Type on a shift.
NO_SHIFT_DAY_TYPES = ("Off Day", "Rest Day", "Public Holiday")


class RosterDay(Document):
	"""One person's Day Type for one date, with no shift attached.

	The name is "{employee}-{date}", so the primary key allows one marker per
	person per day. hrms.utils.ot_calculation._read_rostered_day_types reads it
	before any Shift Assignment; hrms.api.roster.set_day_type writes it.
	"""

	def validate(self):
		# Desk writes the doctype directly, past set_day_type's own check
		if self.day_type not in NO_SHIFT_DAY_TYPES:
			frappe.throw(_("Day Type must be one of {0}.").format(", ".join(NO_SHIFT_DAY_TYPES)))


def marked_day_off(employee, day) -> bool:
	"""HR marked this date Off / Rest / Public Holiday with no shift: a day off on every screen
	that asks "is this a working day" (owner, 7 Oct 2026). A site not migrated yet has no table."""
	if not frappe.db.table_exists("Roster Day"):
		return False
	return bool(frappe.db.get_value("Roster Day", {"employee": employee, "date": str(day)}, "day_type"))
