import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time


class ShiftBreak(Document):
	@property
	def duration(self):
		"""The `duration` virtual DocField: what this break actually deducts, in hours.

		Fixed rows deduct their Start-End window; Flexible rows deduct the entered
		break_hours. The grid used to surface break_hours for BOTH types, so every
		Fixed row showed a dead 0.00 — break_hours is a Flexible-only input the
		Fixed path never reads — and the one complaint this produced ("break
		duration tak reflect") arrived while the deduction was working fine.

		Virtual on purpose: computed on read from the SAME fields the deduction
		engine (hrms.utils.break_calculation) reads, so display and engine cannot
		drift, and no stored copy exists to go stale under the write paths that
		skip validate — the shadow sync inserts Shift Types with ignore_validate,
		and data import / db.set_value never ran it either.

		Never raises: this renders inside a grid, and a half-filled draft row must
		not break the form. Missing inputs -> None, shown blank.
		"""
		if (self.break_type or "Fixed") == "Flexible":
			return self.break_hours or None
		if not self.start_time or not self.end_time:
			return None
		try:
			start, end = get_time(self.start_time), get_time(self.end_time)
		except Exception:
			return None
		seconds = (
			(end.hour - start.hour) * 3600 + (end.minute - start.minute) * 60 + (end.second - start.second)
		)
		if seconds <= 0:
			return None
		return round(seconds / 3600, 2)

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
