# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import logging
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, getdate

logger = logging.getLogger(__name__)

from hrms.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from hrms.hr.utils import (
	get_distance_between_coordinates,
	set_geolocation_from_coordinates,
	validate_active_employee,
)


class CheckinRadiusExceededError(frappe.ValidationError):
	pass


class EmployeeCheckin(Document):
	def before_validate(self):
		self.time = get_datetime(self.time).replace(microsecond=0)

	def validate(self):
		validate_active_employee(self.employee)
		self.validate_duplicate_log()
		self.validate_time_change()
		self.fetch_shift()
		self.set_geolocation()
		self.validate_distance_from_shift_location()

	def validate_duplicate_log(self):
		doc = frappe.db.exists(
			"Employee Checkin",
			{
				"employee": self.employee,
				"time": self.time,
				"name": ("!=", self.name),
				"log_type": self.log_type,
			},
		)
		if doc:
			doc_link = frappe.get_desk_link("Employee Checkin", doc)
			frappe.throw(
				_("This employee already has a log with the same timestamp.{0}").format("<Br>" + doc_link)
			)

	def validate_time_change(self):
		if self.attendance and self.has_value_changed("time"):
			frappe.throw(
				title=_("Cannot Modify Time"),
				msg=_(
					"An attendance record is linked to this checkin. Please cancel the attendance before modifying time."
				),
			)

	@frappe.whitelist()
	def set_geolocation(self):
		set_geolocation_from_coordinates(self)

	@frappe.whitelist()
	def fetch_shift(self):
		if not (
			shift_actual_timings := get_actual_start_end_datetime_of_shift(
				self.employee, get_datetime(self.time), True
			)
		):
			self.shift = None
			self.offshift = 1
			return

		if (
			shift_actual_timings.shift_type.determine_check_in_and_check_out
			== "Strictly based on Log Type in Employee Checkin"
			and not self.log_type
			and not self.skip_auto_attendance
		):
			frappe.throw(
				_("Log Type is required for check-ins falling in the shift: {0}.").format(
					shift_actual_timings.shift_type.name
				)
			)
		if not self.attendance:
			self.offshift = 0
			self.shift = shift_actual_timings.shift_type.name
			self.shift_actual_start = shift_actual_timings.actual_start
			self.shift_actual_end = shift_actual_timings.actual_end
			self.shift_start = shift_actual_timings.start_datetime
			self.shift_end = shift_actual_timings.end_datetime
			self.overtime_type = shift_actual_timings.overtime_type or None

	def validate_distance_from_shift_location(self):
		# Per company — geolocated check-in is a per-entity rollout decision.
		from hrms.utils.company_settings import is_setting_enabled_for_employee

		if not is_setting_enabled_for_employee(self.employee, "allow_geolocation_tracking"):
			return

		if not (self.latitude or self.longitude):
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		assignment_locations = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"shift_type": self.shift,
				"start_date": ["<=", self.time],
				"shift_location": ["is", "set"],
				"docstatus": 1,
				"status": "Active",
			},
			or_filters=[["end_date", ">=", self.time], ["end_date", "is", "not set"]],
			pluck="shift_location",
		)
		if not assignment_locations:
			return

		checkin_radius, latitude, longitude = frappe.db.get_value(
			"Shift Location", assignment_locations[0], ["checkin_radius", "latitude", "longitude"]
		)
		if checkin_radius <= 0:
			return

		distance = get_distance_between_coordinates(latitude, longitude, self.latitude, self.longitude)
		if distance > checkin_radius:
			frappe.throw(
				_("You must be within {0} meters of your shift location to check in.").format(checkin_radius),
				exc=CheckinRadiusExceededError,
			)


@frappe.whitelist()
def add_log_based_on_employee_field(
	employee_field_value: str | int,
	timestamp: str | datetime,
	device_id: str | int | None = None,
	log_type: str | None = None,
	skip_auto_attendance: str | bool | int = 0,
	employee_fieldname: str = "attendance_device_id",
	latitude: str | float | None = None,
	longitude: str | float | None = None,
) -> Document:
	"""Finds the relevant Employee using the employee field value and creates a Employee Checkin.

	:param employee_field_value: The value to look for in employee field.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id: (optional)Location / Device ID. A short string is expected.
	:param log_type: (optional)Direction of the Punch if available (IN/OUT).
	:param skip_auto_attendance: (optional)Skip auto attendance field will be set for this log(0/1).
	:param employee_fieldname: (Default: attendance_device_id)Name of the field in Employee DocType based on which employee lookup will happen.
	:latitude: (optional) Latitude of the shift location.
	:longitude: (optional) Longitude of the shift location.
	"""

	# staff lockdown: this is a device/integration endpoint — the caller must
	# hold real create permission on Employee Checkin (staff roles are
	# read-only and punch via hrms.api.remote_checkin.punch instead)
	if not frappe.has_permission("Employee Checkin", "create"):
		frappe.throw(_("Not permitted to create Employee Checkin."), frappe.PermissionError)

	if not employee_field_value or not timestamp:
		frappe.throw(_("'employee_field_value' and 'timestamp' are required."))

	allowed_employee_fieldnames = {"name", "employee", "attendance_device_id"}
	if employee_fieldname not in allowed_employee_fieldnames:
		frappe.throw(
			_("'employee_fieldname' must be one of {0}.").format(", ".join(allowed_employee_fieldnames))
		)

	employee = frappe.db.get_values(
		"Employee",
		{employee_fieldname: employee_field_value},
		["name", "employee_name", employee_fieldname],
		as_dict=True,
	)
	if employee:
		employee = employee[0]
	else:
		frappe.throw(
			_("No Employee found for the given employee field value. '{}': {}").format(
				employee_fieldname, employee_field_value
			)
		)

	doc = frappe.new_doc("Employee Checkin")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	doc.latitude = latitude
	doc.longitude = longitude
	if cint(skip_auto_attendance) == 1:
		doc.skip_auto_attendance = "1"
	doc.insert()

	return doc


@frappe.whitelist()
def bulk_fetch_shift(checkins: list[str] | str) -> None:
	if isinstance(checkins, str):
		checkins = frappe.json.loads(checkins)
	for d in checkins:
		doc = frappe.get_doc("Employee Checkin", d)
		doc.fetch_shift()
		doc.flags.ignore_validate = True
		doc.save()


def mark_attendance_and_link_log(
	logs: list[Document],
	attendance_status: str,
	attendance_date: str | date,
	working_hours: float | None = None,
	late_entry: int | bool = False,
	early_exit: int | bool = False,
	in_time: datetime | None = None,
	out_time: datetime | None = None,
	shift: str | None = None,
	overtime_type: str | None = None,
	repair_attendance: Document | None = None,
) -> Document | None:
	"""Creates an attendance and links the attendance to the Employee Checkin.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Checkin'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	log_names = [x.name for x in logs]
	employee = logs[0].employee

	if attendance_status == "Skip":
		skip_attendance_in_checkins(log_names)
		return None

	if attendance_status not in ("Present", "Absent", "Half Day"):
		frappe.throw(_("{0} is an invalid Attendance Status.").format(attendance_status))

	try:
		frappe.db.savepoint("attendance_creation")

		attendance = create_or_update_attendance(
			employee=employee,
			attendance_date=attendance_date,
			attendance_status=attendance_status,
			working_hours=working_hours,
			shift=shift,
			late_entry=late_entry,
			early_exit=early_exit,
			in_time=in_time,
			out_time=out_time,
			overtime_type=overtime_type,
			repair_attendance=repair_attendance,
		)

		if attendance_status == "Absent":
			attendance.add_comment(
				text=_("Employee was marked Absent for not meeting the working hours threshold.")
			)

		update_attendance_in_checkins(log_names, attendance.name)
		return attendance

	except frappe.ValidationError as e:
		handle_attendance_exception(log_names, e)
		return None


def create_or_update_attendance(
	employee,
	attendance_date,
	attendance_status,
	working_hours=None,
	shift=None,
	late_entry=False,
	early_exit=False,
	in_time=None,
	out_time=None,
	overtime_type=None,
	repair_attendance=None,
):
	"""Creates a new attendance, repairs a provisional auto-Absent, or updates
	an existing half-day attendance."""
	if repair_attendance is not None:
		if (
			not isinstance(repair_attendance, Document)
			or repair_attendance.doctype != "Attendance"
			or not cint(repair_attendance.auto_attendance)
			or repair_attendance.get("synced_from_instance")
			or cint(repair_attendance.docstatus) != 0
			or repair_attendance.employee != employee
			or repair_attendance.shift != shift
			or getdate(repair_attendance.attendance_date) != getdate(attendance_date)
		):
			frappe.throw(_("Attendance repair requires the matching automation-owned draft."))
		logger.info("[checkin] saving trusted attendance repair through document validation")
	if repair_attendance is None and (
		attendance := get_existing_half_day_attendance(employee, attendance_date)
	):
		frappe.db.set_value(
			"Attendance",
			attendance.name,
			{
				"working_hours": working_hours,
				"shift": shift,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"in_time": in_time,
				"out_time": out_time,
				"half_day_status": "Absent" if attendance_status == "Absent" else "Present",
				"modify_half_day_status": 0,
			},
		)
		return frappe.get_doc("Attendance", attendance.name)

	if repair_attendance is None and (absence := get_repairable_auto_absence(employee, attendance_date)):
		# Auto-attendance marked this day Absent because no check-ins had
		# arrived; the authoritative punches are here now.
		return _replace_provisional_absence(
			absence,
			employee=employee,
			attendance_date=attendance_date,
			attendance_status=attendance_status,
			working_hours=working_hours,
			shift=shift,
			late_entry=late_entry,
			early_exit=early_exit,
			in_time=in_time,
			out_time=out_time,
			overtime_type=overtime_type,
		)

	attendance = repair_attendance if repair_attendance is not None else frappe.new_doc("Attendance")
	was_new = attendance.is_new()
	attendance.update(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": attendance_date,
			"status": attendance_status,
			"working_hours": working_hours,
			"shift": shift,
			"late_entry": late_entry,
			"early_exit": early_exit,
			"in_time": in_time,
			"out_time": out_time,
			# Automation-owned, so a later provisional Absent can be told apart
			# from a person's manual Attendance.
			"auto_attendance": 1,
		}
	)

	if repair_attendance is not None:
		attendance.update({"overtime_type": None, "standard_working_hours": 0, "actual_overtime_duration": 0})

	# Set overtime data if applicable
	if overtime_type and attendance_status == "Present":
		overtime_data = get_overtime_data(shift, working_hours)
		if overtime_data:
			attendance.update(
				{
					"overtime_type": overtime_type,
					"standard_working_hours": overtime_data.get("standard_working_hours"),
					"actual_overtime_duration": overtime_data.get("actual_overtime_duration"),
				}
			)
	if repair_attendance is not None:
		attendance.save(ignore_permissions=True)
	else:
		attendance.save()
	if repair_attendance is None or was_new:
		attendance.submit()

	return attendance


def _replace_provisional_absence(absence, **fields):
	"""Replace a submitted provisional auto-Absent with the day the punches prove.

	The provisional row is SUBMITTED, so its status, hours and overtime cannot
	change through validation. Writing them with db.set_value skipped
	Attendance.validate: set_overtime never ran, and the day read Present with
	0 h overtime and no rate bands (Astra's 360 audit, ATT-PROVISIONAL). Do it
	the way the late-checkout repair does — cancel the automation-owned row
	and re-mark the day through insert -> validate -> submit under a
	savepoint — and refuse when payroll or an approved claim already depends
	on the day, so a paid Absent is never silently turned into a Present."""
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	employee = fields["employee"]
	attendance_date = fields["attendance_date"]
	status = fields["attendance_status"]
	if _repair_financial_dependency(employee, attendance_date, absence.name):
		logger.warning(
			"[checkin] provisional Absent %s for %s on %s has a financial dependency — left for HR",
			absence.name,
			employee,
			attendance_date,
		)
		frappe.throw(
			_(
				"Approved overtime, replacement leave or submitted payroll already depends on {0}; "
				"the auto-marked Absent {1} needs a manual correction."
			).format(attendance_date, absence.name)
		)

	frappe.db.savepoint("provisional_absence_repair")
	try:
		absence.flags.ignore_permissions = True
		absence.cancel()
		replacement = frappe.new_doc("Attendance")
		# Automation-owned, like the row it replaces: the manual "process
		# attendance" button runs this under whoever pressed it.
		replacement.flags.ignore_permissions = True
		replacement.update(
			{
				"employee": employee,
				"attendance_date": attendance_date,
				"status": status,
				"working_hours": fields["working_hours"],
				"shift": fields["shift"],
				"late_entry": fields["late_entry"],
				"early_exit": fields["early_exit"],
				"in_time": fields["in_time"],
				"out_time": fields["out_time"],
				"auto_attendance": 1,
				"amended_from": absence.name,
			}
		)
		if fields.get("overtime_type") and status == "Present":
			overtime_data = get_overtime_data(fields["shift"], fields["working_hours"])
			if overtime_data:
				replacement.update(
					{
						"overtime_type": fields["overtime_type"],
						"standard_working_hours": overtime_data.get("standard_working_hours"),
						"actual_overtime_duration": overtime_data.get("actual_overtime_duration"),
					}
				)
		replacement.insert()
		replacement.submit()
		replacement.add_comment(
			"Comment",
			_("Auto-marked Absent {0} replaced with {1} when check-ins arrived late.").format(
				absence.name, _(status)
			),
		)
	except Exception as exc:
		frappe.db.rollback(save_point="provisional_absence_repair")
		logger.exception(
			"[checkin] provisional Absent %s replacement rolled back for %s on %s",
			absence.name,
			employee,
			attendance_date,
		)
		if isinstance(exc, frappe.ValidationError):
			raise
		# A lock wait, a permission refusal or any other non-validation failure
		# must cost this employee's day, not every employee and shift after it
		# in the hourly run: the caller only catches ValidationError, and turns
		# it into skipped punches with a comment HR can act on.
		frappe.throw(
			_(
				"Replacing the auto-marked Absent {0} failed ({1}); the punches for {2} need a manual review."
			).format(absence.name, type(exc).__name__, attendance_date)
		)
	logger.info(
		"[checkin] provisional Absent %s replaced by %s (%s) for %s on %s",
		absence.name,
		replacement.name,
		status,
		employee,
		attendance_date,
	)
	return replacement


def get_repairable_auto_absence(employee, attendance_date) -> Document | None:
	"""An auto-attendance Absent that no check-in ever backed — the provisional
	absence mark_absent_for_dates_with_no_attendance leaves when punches are
	missing. Manual Absents (auto_attendance=0) and punch-derived Absents
	(which have linked check-ins) are deliberately excluded, so a real HR
	decision is never overwritten."""
	name = frappe.db.exists(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": attendance_date,
			"status": "Absent",
			"auto_attendance": 1,
			"docstatus": 1,
		},
	)
	if not name:
		return None
	if frappe.db.exists("Employee Checkin", {"attendance": name}):
		return None
	logger.info("[checkin] found provisional auto-Absent %s for %s", name, employee)
	return frappe.get_doc("Attendance", name)


def get_overtime_data(shift_name, working_hours):
	overtime_data = {}

	shift_type_details = frappe.db.get_value(
		doctype="Shift Type",
		filters={"name": shift_name},
		fieldname=["allow_overtime", "start_time", "end_time"],
		as_dict=True,
	)

	if not shift_type_details or not shift_type_details.allow_overtime:
		return overtime_data

	standard_working_hours = calculate_time_difference(
		shift_type_details.start_time, shift_type_details.end_time
	)

	if working_hours > standard_working_hours:
		actual_overtime_duration = working_hours - standard_working_hours
		overtime_data = {
			"standard_working_hours": standard_working_hours,
			"actual_overtime_duration": actual_overtime_duration,
		}

	return overtime_data


def get_existing_half_day_attendance(employee, attendance_date):
	attendance_name = frappe.db.exists(
		"Attendance",
		{
			"employee": employee,
			"attendance_date": attendance_date,
			"status": "Half Day",
			"modify_half_day_status": 1,
			"leave_type": ("is", "set"),
		},
	)

	if attendance_name:
		attendance_doc = frappe.get_doc("Attendance", attendance_name)
		return attendance_doc
	return None


def calculate_working_hours(logs, check_in_out_type, working_hours_calc_type):
	"""Given a set of logs in chronological order calculates the total working hours based on the parameters.
	Zero is returned for all invalid cases.

	:param logs: The List of 'Employee Checkin'.
	:param check_in_out_type: One of: 'Alternating entries as IN and OUT during the same shift', 'Strictly based on Log Type in Employee Checkin'
	:param working_hours_calc_type: One of: 'First Check-in and Last Check-out', 'Every Valid Check-in and Check-out'
	"""
	total_hours = 0
	in_time = out_time = None
	if check_in_out_type == "Alternating entries as IN and OUT during the same shift":
		in_time = logs[0].time
		if len(logs) >= 2:
			out_time = logs[-1].time
		if working_hours_calc_type == "First Check-in and Last Check-out":
			# assumption in this case: First log always taken as IN, Last log always taken as OUT
			total_hours = time_diff_in_hours(in_time, logs[-1].time)
		elif working_hours_calc_type == "Every Valid Check-in and Check-out":
			logs = logs[:]
			while len(logs) >= 2:
				total_hours += time_diff_in_hours(logs[0].time, logs[1].time)
				del logs[:2]

	elif check_in_out_type == "Strictly based on Log Type in Employee Checkin":
		if working_hours_calc_type == "First Check-in and Last Check-out":
			first_in_log_index = find_index_in_dict(logs, "log_type", "IN")
			first_in_log = logs[first_in_log_index] if first_in_log_index or first_in_log_index == 0 else None
			last_out_log_index = find_index_in_dict(reversed(logs), "log_type", "OUT")
			last_out_log = (
				logs[len(logs) - 1 - last_out_log_index]
				if last_out_log_index or last_out_log_index == 0
				else None
			)
			in_time = getattr(first_in_log, "time", None)
			out_time = getattr(last_out_log, "time", None)
			if first_in_log and last_out_log:
				total_hours = time_diff_in_hours(in_time, out_time)
		elif working_hours_calc_type == "Every Valid Check-in and Check-out":
			in_log = out_log = None
			for log in logs:
				if in_log and out_log:
					if not in_time:
						in_time = in_log.time
					out_time = out_log.time
					total_hours += time_diff_in_hours(in_log.time, out_log.time)
					in_log = out_log = None
				if not in_log:
					in_log = log if log.log_type == "IN" else None
					if in_log and not in_time:
						in_time = in_log.time
				elif not out_log:
					out_log = log if log.log_type == "OUT" else None

			if in_log and out_log:
				out_time = out_log.time
				total_hours += time_diff_in_hours(in_log.time, out_log.time)

	return total_hours, in_time, out_time


def worked_intervals(logs, check_in_out_type, working_hours_calc_type):
	"""The (start, end) pairs calculate_working_hours counts as worked, in order.

	Under "First Check-in and Last Check-out" the whole first-IN..last-OUT span
	is one interval (gaps inside it are paid); under "Every Valid Check-in and
	Check-out" each IN/OUT pair is one. Break deduction needs WHERE the time was
	worked, not just how much: an unrelated logout must not hide a fixed lunch.
	hrms/tests/test_break_deduction_worked_intervals.py pins the sum of these
	intervals to calculate_working_hours for every policy.
	"""
	if check_in_out_type == "Alternating entries as IN and OUT during the same shift":
		if working_hours_calc_type == "First Check-in and Last Check-out":
			return [(logs[0].time, logs[-1].time)] if len(logs) >= 2 else []
		return [(a.time, b.time) for a, b in zip(logs[0::2], logs[1::2], strict=False)]
	if check_in_out_type != "Strictly based on Log Type in Employee Checkin":
		return []
	if working_hours_calc_type == "First Check-in and Last Check-out":
		ins = [log.time for log in logs if log.log_type == "IN"]
		outs = [log.time for log in logs if log.log_type == "OUT"]
		return [(ins[0], outs[-1])] if ins and outs else []
	pairs = []
	in_log = None
	for log in logs:
		if in_log is None:
			in_log = log if log.log_type == "IN" else None
		elif log.log_type == "OUT":  # a second IN keeps the first, as the native loop does
			pairs.append((in_log.time, log.time))
			in_log = None
	logger.debug("[employee_checkin] %d worked interval(s) from %d punch(es)", len(pairs), len(logs))
	return pairs


def time_diff_in_hours(start, end):
	return round(float((end - start).total_seconds()) / 3600, 2)


def find_index_in_dict(dict_list, key, value):
	return next((index for (index, d) in enumerate(dict_list) if d[key] == value), None)


def handle_attendance_exception(log_names: list, error_message: str):
	frappe.db.rollback(save_point="attendance_creation")
	frappe.clear_messages()
	skip_attendance_in_checkins(log_names)
	add_comment_in_checkins(log_names, error_message)


def add_comment_in_checkins(log_names: list, error_message: str):
	text = "{prefix}<br>{error_message}".format(
		prefix=frappe.bold(_("Reason for skipping auto attendance:")), error_message=error_message
	)

	for name in log_names:
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Employee Checkin",
				"reference_name": name,
				"content": text,
			}
		).insert(ignore_permissions=True)


def skip_attendance_in_checkins(log_names: list):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("skip_auto_attendance", 1)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()


def update_attendance_in_checkins(log_names: list, attendance_id: str):
	EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
	(
		frappe.qb.update(EmployeeCheckin)
		.set("attendance", attendance_id)
		.where(EmployeeCheckin.name.isin(log_names))
	).run()


def calculate_time_difference(start_time, end_time):
	if end_time < start_time:
		end_time += timedelta(days=1)
	time_difference = abs(start_time - end_time)

	return round(time_difference.total_seconds() / 3600, 2)
