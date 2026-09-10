"""A day's punches, through the real resolver and the real hourly job.

The defects these pin were all invisible to mocked tests: the resolver, the
job and the hours arithmetic each looked right on their own while the day came
out wrong. Every case builds a synthetic employee inside a savepoint and reads
back the Attendance row the job actually wrote.

Needs a site:  cd ~/verify-bench && bench --site fresh.local run-tests \\
                   --module hrms.tests.test_checkin_day_end_to_end
"""

import datetime
import unittest

import frappe

DAY = datetime.date(2026, 9, 10)
SHIFT = "T2E 9-6"


def at(day_offset, hour, minute=0):
	return datetime.datetime.combine(DAY + datetime.timedelta(days=day_offset), datetime.time(hour, minute))


class TestADayEndToEnd(unittest.TestCase):
	"""One employee, one 09:00-18:00 assignment, punches in, punches out."""

	def setUp(self):
		frappe.db.savepoint("t2e")
		self.addCleanup(frappe.db.rollback, save_point="t2e")
		frappe.set_user("Administrator")
		self.company = frappe.db.get_value("Company", {}, "name")
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc(
				{
					"doctype": "Shift Type",
					"name": SHIFT,
					"start_time": "09:00:00",
					"end_time": "18:00:00",
					"enable_auto_attendance": 1,
					"process_attendance_after": "2026-09-01",
					"last_sync_of_checkin": "2026-09-15 00:00:00",
					"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
					"working_hours_calculation_based_on": "First Check-in and Last Check-out",
					"working_hours_threshold_for_half_day": 4,
					"working_hours_threshold_for_absent": 0,
				}
			).insert(ignore_permissions=True)
		self.employee = (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": "T2E Probe",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2026-01-01",
					"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
					"company": self.company,
					"status": "Active",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee,
				"shift_type": SHIFT,
				"start_date": "2026-09-01",
				"status": "Active",
				"company": self.company,
			}
		)
		assignment.flags.ignore_permissions = True
		assignment.insert()
		assignment.submit()

	def punch(self, log_type, when):
		doc = frappe.new_doc("Employee Checkin")
		doc.update({"employee": self.employee, "log_type": log_type, "time": when})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc

	def day(self):
		frappe.get_doc("Shift Type", SHIFT).process_auto_attendance()
		return frappe.db.get_value(
			"Attendance",
			{"employee": self.employee, "attendance_date": DAY, "docstatus": 1},
			["status", "working_hours", "in_time", "out_time"],
			as_dict=True,
		)

	def test_an_ordinary_day(self):
		self.punch("IN", at(0, 9, 30))
		self.punch("OUT", at(0, 18, 5))
		row = self.day()
		self.assertEqual(row.status, "Present")
		self.assertAlmostEqual(row.working_hours, 8.58, places=2)

	def test_working_past_midnight_is_paid_not_discarded(self):
		"""Nabil, 10 Sep: 09:30 to 00:32 on a 9-6 shift. The check-out was more
		than an hour past the shift end, so it used to be filed off-shift and
		fifteen hours were recorded as none."""
		self.punch("IN", at(0, 9, 30))
		out = self.punch("OUT", at(1, 0, 32))
		self.assertEqual(out.shift, SHIFT)
		self.assertEqual(out.offshift, 0)
		row = self.day()
		self.assertEqual(row.status, "Present")
		self.assertAlmostEqual(row.working_hours, 15.03, places=2)
		self.assertEqual(row.out_time, at(1, 0, 32))

	def test_arriving_early_is_presence_but_not_paid(self):
		"""HR's ruling: the arrival is recorded as it happened, and the paid
		hours start when the shift starts."""
		self.punch("IN", at(0, 7, 30))
		self.punch("OUT", at(0, 18, 5))
		row = self.day()
		self.assertEqual(row.status, "Present")
		self.assertEqual(row.in_time, at(0, 7, 30), "the real arrival is kept")
		self.assertAlmostEqual(row.working_hours, 9.08, places=2, msg="paid from 09:00, not 07:30")

	def _an_overtime_type(self) -> str:
		ot_type = frappe.db.get_value("Overtime Type", {}, "name")
		if not ot_type:
			component = frappe.db.get_value("Salary Component", {"type": "Earning"}, "name")
			if not component:
				self.skipTest("no Salary Component on this site to hang an Overtime Type on")
			ot_type = (
				frappe.get_doc(
					{
						"doctype": "Overtime Type",
						"__newname": "T2E Probe OT Type",
						"standard_multiplier": 1.5,
						"applicable_salary_component": [{"salary_component": component}],
						"overtime_salary_component": component,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		return ot_type

	def test_the_overtime_type_survives_an_early_arrival(self):
		"""The hourly job reads the day's overtime type off the FIRST eligible
		punch. An early arrival is first by definition, so a punch stamped by
		the early-arrival path without an overtime type silently makes the
		whole day ineligible for overtime."""
		ot_type = self._an_overtime_type()
		frappe.db.set_value("Shift Type", SHIFT, "overtime_type", ot_type)
		frappe.db.set_value(
			"Shift Assignment",
			{"employee": self.employee, "docstatus": 1},
			"overtime_type",
			ot_type,
		)

		early_in = self.punch("IN", at(0, 7, 30))
		out = self.punch("OUT", at(0, 20, 5))
		self.assertEqual(early_in.overtime_type, ot_type, "the early IN lost the shift's overtime type")
		self.assertEqual(out.overtime_type, ot_type, "the OUT closing the session lost it too")

	def test_arrival_time_never_decides_the_overtime_type(self):
		"""The assignment decides, and nothing else. Upstream's get_shift_for_time
		overwrites the shift type's overtime type with `assignment.overtime_type
		or None`, so a resolver that falls back to the Shift Type makes an early
		punch OT-eligible on an assignment that says it is not — and the whole
		day follows the first punch. Pay must not be a function of arrival time."""
		ot_type = self._an_overtime_type()
		# the shift carries a type; the submitted assignment deliberately does not
		frappe.db.set_value("Shift Type", SHIFT, "overtime_type", ot_type)
		frappe.db.set_value(
			"Shift Assignment", {"employee": self.employee, "docstatus": 1}, "overtime_type", None
		)

		on_time = self.punch("IN", at(0, 9, 30)).overtime_type
		frappe.db.delete("Employee Checkin", {"employee": self.employee})
		early = self.punch("IN", at(0, 7, 30)).overtime_type

		self.assertEqual(
			on_time,
			early,
			"an early arrival resolved a different overtime type than an on-time one — "
			"overtime became a function of what time you walked in",
		)

	def test_a_forgotten_check_out_is_not_a_half_day(self):
		self.punch("IN", at(0, 9, 30))
		row = self.day()
		self.assertEqual(row.status, "Half Day")
		self.assertEqual(row.working_hours, 0)


if __name__ == "__main__":
	unittest.main()
