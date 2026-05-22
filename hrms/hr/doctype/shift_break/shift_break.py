import frappe
from frappe import _
from frappe.model.document import Document


class ShiftBreak(Document):
	def validate(self):
		if self.start_time and self.end_time and self.end_time <= self.start_time:
			frappe.throw(
				_("Shift Break end time must be after start time (row: {0} {1}).").format(
					self.day_of_week, self.period
				)
			)
