# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from datetime import datetime, time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_year_ending, get_year_start, getdate

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.attendance_request.attendance_request import OverlappingAttendanceRequestError
from hrms.hr.doctype.leave_application.test_leave_application import make_allocation_record
from hrms.payroll.doctype.salary_slip.test_salary_slip import (
	make_holiday_list,
	make_leave_application,
)
from hrms.tests.test_utils import add_date_to_holiday_list, get_first_sunday

test_dependencies = ["Employee"]


class TestAttendanceRequest(FrappeTestCase):
	def setUp(self):
		for doctype in ["Attendance Request", "Attendance"]:
			frappe.db.delete(doctype)

		self.from_date = get_year_start(add_months(getdate(), -1))
		self.to_date = get_year_ending(getdate())
		self.holiday_list = make_holiday_list(
			from_date=self.from_date, to_date=self.to_date, add_weekly_offs=False
		)

		self.employee = get_employee()
		frappe.db.set_value("Employee", self.employee.name, "holiday_list", self.holiday_list)

	def test_attendance_request_overlap(self):
		create_attendance_request(employee=self.employee.name, reason="On Duty", company="_Test Company")

		today = getdate()
		dateranges = [
			(add_days(today, -2), today),
			(today, today),
			(today, add_days(today, 1)),
			(add_days(today, -2), add_days(today, 2)),
		]
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"reason": "On Duty",
				"company": "_Test Company",
			}
		)

		for entry in dateranges:
			attendance_request.from_date = entry[0]
			attendance_request.to_date = entry[1]
			self.assertRaises(OverlappingAttendanceRequestError, attendance_request.save)

		# no overlap
		attendance_request.from_date = add_days(today, -3)
		attendance_request.to_date = add_days(today, -2)
		attendance_request.save()

	def test_on_duty_attendance_request(self):
		"Test creation of Attendance from Attendance Request, on duty."
		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="On Duty", company="_Test Company"
		)
		records = self.get_attendance_records(attendance_request.name)

		self.assertEqual(len(records), 2)
		self.assertEqual(records[0].status, "Present")
		self.assertEqual(records[0].docstatus, 1)

		# cancelling attendance request cancels linked attendances
		attendance_request.cancel()

		# cancellation alters docname
		# fetch attendance value again to avoid stale docname
		records = self.get_attendance_records(attendance_request.name)
		self.assertEqual(records[0].docstatus, 2)

	def test_work_from_home_attendance_request(self):
		"Test creation of Attendance from Attendance Request, work from home."
		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="Work From Home", company="_Test Company"
		)
		records = self.get_attendance_records(attendance_request.name)

		self.assertEqual(records[0].status, "Work From Home")

		# cancelling attendance request cancels linked attendances
		attendance_request.cancel()
		records = self.get_attendance_records(attendance_request.name)
		self.assertEqual(records[0].docstatus, 2)

	def test_overwrite_attendance(self):
		attendance_name = mark_attendance(self.employee.name, getdate(), "Absent")

		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="Work From Home", company="_Test Company"
		)
		prev_attendance = frappe.get_doc("Attendance", attendance_name)

		# attendance request should overwrite attendance status from Absent to Work From Home
		self.assertEqual(prev_attendance.status, "Work From Home")
		self.assertEqual(prev_attendance.attendance_request, attendance_request.name)

	def test_skip_attendance_on_holiday(self):
		today = getdate()
		add_date_to_holiday_list(today, self.holiday_list)

		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="On Duty", company="_Test Company"
		)

		records = self.get_attendance_records(attendance_request.name)
		# only 1 attendance marked for yesterday
		# attendance skipped for today since its a holiday
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0].status, "Present")

	def test_skip_attendance_on_leave(self):
		frappe.delete_doc_if_exists("Leave Type", "Test Skip Attendance", force=1)
		leave_type = frappe.get_doc(
			dict(leave_type_name="Test Skip Attendance", doctype="Leave Type")
		).insert()

		make_allocation_record(leave_type=leave_type.name, from_date=self.from_date, to_date=self.to_date)
		today = getdate()
		make_leave_application(self.employee.name, today, today, leave_type.name)

		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="On Duty", company="_Test Company"
		)
		records = self.get_attendance_records(attendance_request.name)

		# only 1 attendance marked for yesterday
		# attendance skipped for today since its a leave
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0].attendance_date, add_days(today, -1))
		self.assertEqual(records[0].status, "Present")

	def test_include_holidays_check(self):
		# Create a holiday on today's date
		today = getdate()
		add_date_to_holiday_list(today, self.holiday_list)

		# Create an Attendance Request with include_holidays checked
		attendance_request = create_attendance_request(
			employee=self.employee.name,
			reason="On Duty",
			company="_Test Company",
			include_holidays=1,  # Set include_holidays to True
		)

		# Check if the attendance record is created on the holiday
		records = self.get_attendance_records(attendance_request.name)
		self.assertEqual(len(records), 2)
		self.assertEqual(records[0].status, "Present")
		self.assertEqual(records[0].attendance_date, today)

	def get_attendance_records(self, attendance_request: str) -> list[dict]:
		return frappe.db.get_all(
			"Attendance",
			{
				"attendance_request": attendance_request,
			},
			["status", "docstatus", "attendance_date"],
		)

	def test_validate_no_attendance_to_create(self):
		today = getdate()
		yesterday = add_days(today, -1)
		# marking absent for two days
		for day in [yesterday, today]:
			mark_attendance(self.employee.name, day, "Present")
		# attendance request with the same status for the same days
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": yesterday,
				"to_date": today,
				"reason": "On Duty",
				"company": "_Test Company",
			}
		)
		self.assertRaises(frappe.ValidationError, attendance_request.save)

		# adding an extra day to the attendance request
		attendance_request.to_date = add_days(today, 1)
		attendance_request.save()
		attach_supporting_file(attendance_request)
		attendance_request.submit()
		# attendance created for the third day
		records = self.get_attendance_records(attendance_request.name)
		self.assertEqual(records[0].status, "Present")

	def test_half_day_status_change(self):
		# when new attendance is created via attendance request
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": getdate(),
				"to_date": getdate(),
				"reason": "On Duty",
				"half_day": 1,
				"half_day_date": getdate(),
				"company": "_Test Company",
			}
		).save()
		attach_supporting_file(attendance_request)
		attendance_request.submit()

		half_day_status = frappe.get_value(
			"Attendance", {"attendance_request": attendance_request.name}, "half_day_status"
		)
		self.assertEqual(half_day_status, "Absent")

	def test_in_out_times_applied_to_created_attendance(self):
		today = getdate()
		attendance_request = create_attendance_request(
			employee=self.employee.name,
			reason="Work From Home",
			company="_Test Company",
			from_date=add_days(today, -1),
			to_date=today,
			in_time="09:00:00",
			out_time="18:00:00",
		)
		records = frappe.db.get_all(
			"Attendance",
			{"attendance_request": attendance_request.name},
			["attendance_date", "in_time", "out_time", "working_hours"],
		)
		self.assertEqual(len(records), 2)
		for record in records:
			self.assertEqual(record.in_time, datetime.combine(record.attendance_date, time(9, 0)))
			self.assertEqual(record.out_time, datetime.combine(record.attendance_date, time(18, 0)))
			self.assertEqual(record.working_hours, 9.0)

	def test_overnight_out_time_lands_on_next_day(self):
		today = getdate()
		attendance_request = create_attendance_request(
			employee=self.employee.name,
			reason="On Duty",
			company="_Test Company",
			from_date=today,
			to_date=today,
			in_time="22:00:00",
			out_time="06:00:00",
		)
		record = frappe.db.get_all(
			"Attendance",
			{"attendance_request": attendance_request.name},
			["attendance_date", "in_time", "out_time", "working_hours"],
		)[0]
		self.assertEqual(record.in_time, datetime.combine(today, time(22, 0)))
		self.assertEqual(record.out_time, datetime.combine(add_days(today, 1), time(6, 0)))
		self.assertEqual(record.working_hours, 8.0)

	def test_one_sided_time_rejected(self):
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": getdate(),
				"to_date": getdate(),
				"reason": "On Duty",
				"company": "_Test Company",
				"in_time": "09:00:00",
			}
		)
		self.assertRaises(frappe.ValidationError, attendance_request.save)

	def test_without_times_attendance_has_no_times(self):
		attendance_request = create_attendance_request(
			employee=self.employee.name, reason="On Duty", company="_Test Company"
		)
		record = frappe.db.get_all(
			"Attendance",
			{"attendance_request": attendance_request.name},
			["in_time", "out_time"],
		)[0]
		self.assertIsNone(record.in_time)
		self.assertIsNone(record.out_time)

	def test_same_in_out_time_rejected(self):
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": getdate(),
				"to_date": getdate(),
				"reason": "On Duty",
				"company": "_Test Company",
				"in_time": "09:00:00",
				"out_time": "09:00:00",
			}
		)
		self.assertRaises(frappe.ValidationError, attendance_request.save)

	def test_half_day_date_keeps_no_times(self):
		today = getdate()
		attendance_request = create_attendance_request(
			employee=self.employee.name,
			reason="On Duty",
			company="_Test Company",
			from_date=add_days(today, -1),
			to_date=today,
			half_day=1,
			half_day_date=today,
			in_time="09:00:00",
			out_time="18:00:00",
		)
		records = {
			r.attendance_date: r
			for r in frappe.db.get_all(
				"Attendance",
				{"attendance_request": attendance_request.name},
				["attendance_date", "status", "in_time", "out_time", "working_hours"],
			)
		}
		self.assertEqual(records[add_days(today, -1)].working_hours, 9.0)
		self.assertEqual(records[today].status, "Half Day")
		self.assertIsNone(records[today].in_time)
		self.assertIsNone(records[today].out_time)

	def test_times_not_applied_to_existing_attendance(self):
		today = getdate()
		existing = mark_attendance(self.employee.name, today, "Absent")

		create_attendance_request(
			employee=self.employee.name,
			reason="Work From Home",
			company="_Test Company",
			from_date=today,
			to_date=today,
			in_time="09:00:00",
			out_time="18:00:00",
		)
		record = frappe.db.get_value("Attendance", existing, ["status", "in_time", "out_time"], as_dict=True)
		# status overwritten, times deliberately untouched
		self.assertEqual(record.status, "Work From Home")
		self.assertIsNone(record.in_time)
		self.assertIsNone(record.out_time)

	def test_submit_without_attachment_blocked(self):
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": getdate(),
				"to_date": getdate(),
				"reason": "On Duty",
				"company": "_Test Company",
			}
		).insert()
		self.assertRaises(frappe.ValidationError, attendance_request.submit)

		attendance_request.reload()
		attach_supporting_file(attendance_request)
		attendance_request.submit()
		self.assertEqual(attendance_request.docstatus, 1)

	def test_self_submission_blocked(self):
		"""Submission is the approval act for this doctype — the employee on the
		request must never submit it themselves, whatever roles (System Manager
		included) they hold."""
		from frappe.utils.user import add_role

		employee = self.employee
		if not employee.user_id:
			employee.user_id = "test_employee@example.com"
			employee.save()
		add_role(employee.user_id, "System Manager")
		# don't strand System Manager on the shared test user if the run commits
		self.addCleanup(lambda: frappe.get_doc("User", employee.user_id).remove_roles("System Manager"))

		today = getdate()
		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": employee.name,
				"from_date": add_days(today, -1),
				"to_date": today,
				"reason": "On Duty",
				"company": "_Test Company",
			}
		).insert()

		frappe.set_user(employee.user_id)
		try:
			self.assertRaises(frappe.ValidationError, attendance_request.submit)
		finally:
			frappe.set_user("Administrator")

		# a different user submitting the same request remains the approval act
		attendance_request.reload()
		attach_supporting_file(attendance_request)
		attendance_request.submit()
		self.assertEqual(attendance_request.docstatus, 1)

	def test_half_day_status_change_when_existing_attendance_is_updated(self):
		# when existing attendance is updated via attendance request
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": self.employee.name,
				"attendance_date": getdate(),
				"status": "Absent",
				"company": "_Test Company",
			}
		).insert()

		attendance_request = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": self.employee.name,
				"from_date": getdate(),
				"to_date": getdate(),
				"reason": "On Duty",
				"half_day": 1,
				"half_day_date": getdate(),
				"company": "_Test Company",
			}
		).save()
		attach_supporting_file(attendance_request)
		attendance_request.submit()

		half_day_status = frappe.get_value(
			"Attendance", {"attendance_request": attendance_request.name}, "half_day_status"
		)
		self.assertEqual(half_day_status, "Absent")


def get_employee():
	return frappe.get_doc("Employee", "_T-Employee-00001")


def attach_supporting_file(doc):
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"supporting-{doc.name}.txt",
			"content": "supporting document",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
		}
	).insert(ignore_permissions=True)


def create_attendance_request(**args: dict) -> dict:
	args = frappe._dict(args)
	today = getdate()

	attendance_request = frappe.get_doc(
		{
			"doctype": "Attendance Request",
			"employee": args.employee or get_employee().name,
			"from_date": add_days(today, -1),
			"to_date": today,
			"reason": "On Duty",
			"company": "_Test Company",
		}
	)

	if args:
		attendance_request.update(args)

	attendance_request.insert()
	attach_supporting_file(attendance_request)
	return attendance_request.submit()
