import frappe
from frappe import _
from frappe.model.document import Document


class ShiftBreak(Document):
	def validate(self):
		if (self.break_type or "Fixed") == "Flexible":
			if not self.break_hours or self.break_hours <= 0:
				frappe.throw(
					_("Flexible Shift Break requires a Break Duration greater than 0 (row: {0} {1}).").format(
						self.day_of_week, self.period
					)
				)
			return

		if not self.start_time or not self.end_time:
			frappe.throw(
				_("Fixed Shift Break requires both Start Time and End Time (row: {0} {1}).").format(
					self.day_of_week, self.period
				)
			)
		if self.end_time <= self.start_time:
			frappe.throw(
				_("Shift Break end time must be after start time (row: {0} {1}).").format(
					self.day_of_week, self.period
				)
			)
