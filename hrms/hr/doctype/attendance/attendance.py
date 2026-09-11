# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import logging
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.terms import ValueWrapper
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	cstr,
	flt,
	format_date,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	nowdate,
)
from frappe.utils.background_jobs import get_job

import hrms
from hrms.hr.doctype.shift_assignment.shift_assignment import has_overlapping_timings
from hrms.hr.offboarding import block_transaction_after_relieving
from hrms.hr.utils import (
	get_holidays_for_employee,
	validate_active_employee,
)
from hrms.utils.holiday_list import get_holiday_dates_between_range
from hrms.utils.identity import get_employee

logger = logging.getLogger(__name__)


class DuplicateAttendanceError(frappe.ValidationError):
	pass


class OverlappingShiftAttendanceError(frappe.ValidationError):
	pass


class Attendance(Document):
	def before_insert(self):
		if self.half_day_status == "":
			self.half_day_status = None

	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home"])
		validate_active_employee(self.employee)
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.validate_overlapping_shift_attendance()
		self.validate_employee_status()
		self.check_leave_record()
		self.claim_hr_ownership_on_amend()
		self.apply_manual_times()
		self.set_overtime()

	def claim_hr_ownership_on_amend(self):
		"""An amendment a person makes is that person's row from then on.

		Frappe's Amend copies `auto_attendance = 1` from the cancelled row, so
		HR's corrected day stayed automation-owned and the next hourly run
		cancelled it and re-marked the day from the punches — the two pages
		disagreeing again an hour after HR fixed them (9 Sep 2026). The job's
		own rebuild says so with `flags.automation_rebuild`; nobody else does.
		"""
		if (
			self.is_new()
			and self.amended_from
			and cint(self.auto_attendance)
			and not getattr(self.flags, "automation_rebuild", False)
		):
			self.auto_attendance = 0
			logger.info(
				"[attendance] amendment of %s by %s is HR-owned from now on",
				self.amended_from,
				frappe.session.user,
			)

	def apply_manual_times(self):
		"""A person's in/out derive the hours; the hourly job's own rows keep theirs.

		The job computes working_hours with breaks deducted and hands the row its
		times and hours together — a raw span must never overwrite that, and its
		times are not checked here: a night shift's first punch legitimately falls
		before midnight of the attendance date. Only times a person typed on a new
		row, or changed on a draft, are validated and turned into hours.
		"""
		if cint(self.auto_attendance):
			# Owned by the job, whether inserted now or a draft the late-checkout
			# repair resaves: its times are punches, not typing, and are not checked.
			return
		before = self.get_doc_before_save()
		typed_new = before is None
		changed = before is not None and _times_differ(before, self)
		if not (typed_new or changed):
			return
		validate_attendance_times(self.in_time, self.out_time, self.attendance_date)
		if self.in_time and self.out_time:
			self.working_hours = paid_hours_for_row(self)
			logger.info(
				"[attendance] hours derived from entered times for %s on %s: %s",
				self.employee,
				self.attendance_date,
				self.working_hours,
			)

	def before_update_after_submit(self):
		"""HR corrected the times on a submitted row: recompute, and say so."""
		before = self.get_doc_before_save()
		if before is None or not _times_differ(before, self):
			return
		validate_attendance_times(self.in_time, self.out_time, self.attendance_date)
		self.flags.hr_corrected_times = True
		old_hours = self.working_hours
		self.working_hours = paid_hours_for_row(self) if self.in_time and self.out_time else 0
		self.set_overtime()
		self.add_comment(
			"Edit",
			_("In/out corrected by {0}: in {1} → {2}, out {3} → {4}; hours {5} → {6}").format(
				frappe.session.user,
				_clock(before.in_time),
				_clock(self.in_time),
				_clock(before.out_time),
				_clock(self.out_time),
				old_hours,
				self.working_hours,
			),
		)
		logger.info(
			"[attendance] %s times corrected on submitted row %s by %s",
			self.employee,
			self.name,
			frappe.session.user,
		)

	def set_overtime(self):
		"""Populate OT hours + rate-band split for this attendance: time worked past
		this record's own shift end (the REAL end, not the padded shift_actual_end
		checkout-grace boundary). Post-shift-end only — pre-shift early check-in is
		never OT. Cleared unless worked + OT-enabled shift + a recorded check-out.
		The ERP stops at hours; pay is computed on the payroll platform."""
		logger.info(
			"[attendance] set_overtime %s %s status=%s", self.employee, self.attendance_date, self.status
		)
		from hrms.utils.ot_calculation import DAY_TYPE_LABELS, get_shift_ot_breakdown

		worked = self.status in ("Present", "Half Day", "Work From Home")
		ot_enabled = self.shift and frappe.db.get_value("Shift Type", self.shift, "enable_overtime")
		if not (worked and ot_enabled and self.out_time):
			self.ot_hours = 0
			self.ot_rate_weighted_hours = 0
			self.set("ot_rate_bands", [])
			return
		breakdown = get_shift_ot_breakdown(
			self.employee, self.shift, self.attendance_date, self.out_time, in_time=self.in_time
		)
		self.ot_hours = breakdown["ot_hours"]
		self.ot_rate_weighted_hours = breakdown["rate_weighted_hours"]
		self.set("ot_rate_bands", [])
		for band in breakdown["bands"]:
			self.append(
				"ot_rate_bands",
				{
					"day_type": DAY_TYPE_LABELS.get(band["day_type"], band["day_type"]),
					"rate": band["rate"],
					"hours": band["hours"],
				},
			)

	def on_cancel(self):
		self.unlink_attendance_from_checkins()

	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		if date_of_joining and getdate(self.attendance_date) < getdate(date_of_joining):
			frappe.throw(
				_("Attendance date {0} can not be less than employee {1}'s joining date: {2}").format(
					frappe.bold(format_date(self.attendance_date)),
					frappe.bold(self.employee),
					frappe.bold(format_date(date_of_joining)),
				)
			)

		block_transaction_after_relieving(self.employee, self.attendance_date, "Attendance")

	def validate_duplicate_record(self):
		duplicate = self.get_duplicate_attendance_record()

		if duplicate:
			frappe.throw(
				_("Attendance for employee {0} is already marked for the date {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(format_date(self.attendance_date)),
					get_link_to_form("Attendance", duplicate),
				),
				title=_("Duplicate Attendance"),
				exc=DuplicateAttendanceError,
			)

	def get_duplicate_attendance_record(self) -> str | None:
		Attendance = frappe.qb.DocType("Attendance")
		query = (
			frappe.qb.from_(Attendance)
			.select(Attendance.name)
			.where(
				(Attendance.employee == self.employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date == self.attendance_date)
				& (Attendance.name != self.name)
				& (
					Attendance.half_day_status.isnull()
					| (Attendance.half_day_status == "")
					| (Attendance.modify_half_day_status == 0)
				)
			)
			.for_update()
		)

		if self.shift:
			query = query.where(
				((Attendance.shift.isnull()) | (Attendance.shift == ""))
				| (
					((Attendance.shift.isnotnull()) | (Attendance.shift != ""))
					& (Attendance.shift == self.shift)
				)
			)

		duplicate = query.run(pluck=True)

		return duplicate[0] if duplicate else None

	def validate_overlapping_shift_attendance(self):
		attendance = self.get_overlapping_shift_attendance()

		if attendance:
			frappe.throw(
				_("Attendance for employee {0} is already marked for an overlapping shift {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(attendance.shift),
					get_link_to_form("Attendance", attendance.name),
				),
				title=_("Overlapping Shift Attendance"),
				exc=OverlappingShiftAttendanceError,
			)

	def get_overlapping_shift_attendance(self) -> dict:
		if not self.shift:
			return {}

		Attendance = frappe.qb.DocType("Attendance")
		same_date_attendance = (
			frappe.qb.from_(Attendance)
			.select(Attendance.name, Attendance.shift)
			.where(
				(Attendance.employee == self.employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date == self.attendance_date)
				& (Attendance.shift != self.shift)
				& (Attendance.name != self.name)
			)
		).run(as_dict=True)

		for d in same_date_attendance:
			if has_overlapping_timings(self.shift, d.shift):
				return d

		return {}

	def validate_employee_status(self):
		if frappe.db.get_value("Employee", self.employee, "status") == "Inactive":
			frappe.throw(_("Cannot mark attendance for an Inactive employee {0}").format(self.employee))

	def check_leave_record(self):
		LeaveApplication = frappe.qb.DocType("Leave Application")
		leave_record = (
			frappe.qb.from_(LeaveApplication)
			.select(
				LeaveApplication.leave_type,
				LeaveApplication.half_day,
				LeaveApplication.half_day_date,
				LeaveApplication.name,
			)
			.where(
				(LeaveApplication.employee == self.employee)
				& (self.attendance_date >= LeaveApplication.from_date)
				& (self.attendance_date <= LeaveApplication.to_date)
				& (LeaveApplication.status == "Approved")
				& (LeaveApplication.docstatus == 1)
			)
		).run(as_dict=True)

		if leave_record:
			for d in leave_record:
				self.leave_type = d.leave_type
				self.leave_application = d.name
				if d.half_day_date == getdate(self.attendance_date):
					self.status = "Half Day"
					frappe.msgprint(
						_("Employee {0} on Half day on {1}").format(
							self.employee, format_date(self.attendance_date)
						)
					)
				else:
					self.status = "On Leave"
					frappe.msgprint(
						_("Employee {0} is on Leave on {1}").format(
							self.employee, format_date(self.attendance_date)
						)
					)

		if self.status in ("On Leave", "Half Day"):
			if not leave_record:
				self.modify_half_day_status = 0
				self.half_day_status = "Absent"
				frappe.msgprint(
					_("No leave record found for employee {0} on {1}").format(
						self.employee, format_date(self.attendance_date)
					),
					alert=1,
				)
		elif self.leave_type:
			self.leave_type = None
			self.leave_application = None

	def validate_employee(self):
		Employee = frappe.qb.DocType("Employee")
		emp = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where((Employee.name == self.employee) & (Employee.status == "Active"))
		).run()
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))

	def unlink_attendance_from_checkins(self):
		EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
		linked_logs = (
			frappe.qb.from_(EmployeeCheckin)
			.select(EmployeeCheckin.name)
			.where(EmployeeCheckin.attendance == self.name)
			.for_update()
			.run(as_dict=True)
		)

		if linked_logs:
			(
				frappe.qb.update(EmployeeCheckin)
				.set("attendance", "")
				.where(EmployeeCheckin.attendance == self.name)
			).run()

			frappe.msgprint(
				msg=_("Unlinked Attendance record from Employee Checkins: {}").format(
					", ".join(get_link_to_form("Employee Checkin", log.name) for log in linked_logs)
				),
				title=_("Unlinked logs"),
				indicator="blue",
				is_minimizable=True,
				wide=True,
			)

	def on_update(self):
		self.publish_update()

	def on_update_after_submit(self):
		"""HR corrected a submitted row: it is HR's from now on, and the PWA hears it.

		`auto_attendance` is not editable after submit through the form, so the
		hand-over is written straight to the row; without it the next hourly
		run treated the corrected row as its own and re-marked the day from the
		punches. `on_update` does not run on an after-submit save, so the
		calendar refetch is published here too.
		"""
		if getattr(self.flags, "hr_corrected_times", False) and cint(self.auto_attendance):
			frappe.db.set_value(self.doctype, self.name, "auto_attendance", 0, update_modified=False)
			self.auto_attendance = 0
			logger.info(
				"[attendance] %s corrected by %s is HR-owned from now on", self.name, frappe.session.user
			)
		self.publish_update()

	def after_delete(self):
		self.publish_update()

	def publish_update(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id", cache=True)
		hrms.refetch_resource("hrms:attendance_calendar_events", employee_user)


def working_hours_between(in_time, out_time, break_minutes=0) -> float:
	"""Paid hours between two entered times, two decimals, less the unpaid break.

	`break_minutes` defaults to 0 so the raw span is still one call away, but a
	caller writing `working_hours` must pass the day's real break. It used to
	take no break at all, which meant a typed correction credited the break as
	worked time while the hourly job deducted it — the same day read 8.95 from
	the job and 10.03 after a five-minute edit (HR-ATT-2026-16073, 10 Sep 2026).

	Floored at zero: a break longer than the span is a misconfiguration, not
	negative work.
	"""
	span = (get_datetime(out_time) - get_datetime(in_time)).total_seconds() / 3600
	return round(max(0.0, span - flt(break_minutes) / 60.0), 2)


def paid_hours_for_row(doc) -> float:
	"""This row's typed times, priced the way the hourly job would price them.

	A plain function rather than a method: the bench-free harness drives the
	controller unbound (`Attendance.apply_manual_times(doc)`) against a stub, so
	a method here would be unreachable from the tests that pin this wiring.
	"""
	shift_start = entered_shift_start(doc.shift, doc.attendance_date)
	breaks = entered_break_minutes(doc.shift, doc.in_time, doc.out_time, doc.company)
	hours = entered_paid_hours(doc.in_time, doc.out_time, shift_start, breaks)
	logger.debug(
		"[attendance] entered times %s-%s on %s: shift start %s, %s break min -> %s h",
		doc.in_time,
		doc.out_time,
		doc.shift,
		shift_start,
		breaks,
		hours,
	)
	return hours


def entered_paid_hours(in_time, out_time, shift_start=None, break_minutes=0) -> float:
	"""Paid hours for typed times, by the SAME three rules the hourly job uses.

	The job applies all three (shift_type.py:551-555): the unpaid early arrival,
	the unpaid break, and hours counted from worked intervals. The typed path
	applied only the break, so a correction to a day with an early punch
	recomputed from that punch: shift 09:00-18:00, in 07:30, out 18:05 gave 9.58
	against the job's own 8.08 for the same times. It never self-healed, because
	correcting a row sets auto_attendance to 0 and the job stops revisiting it.

	Order is part of the rule. The break is measured on the TRIMMED interval —
	`paid_intervals_from` says why in its own docstring: a break configured
	before the shift starts must not be taken off hours that were never counted.

	`shift_start` of None means nothing to trim against (a row whose shift is
	not resolved), and the span stands.
	"""
	from hrms.hr.doctype.shift_type.shift_type import paid_intervals_from

	intervals = [(get_datetime(in_time), get_datetime(out_time))]
	paid, _unpaid_early = paid_intervals_from(intervals, shift_start)
	hours = sum((end - start).total_seconds() for start, end in paid) / 3600
	return round(max(0.0, hours - flt(break_minutes) / 60.0), 2)


def entered_shift_start(shift, attendance_date):
	"""The real shift start for this row's date — the configured time, no grace.

	Mirrors `_real_shift_start_dt` in ot_calculation, which is what overtime
	measures from, so a corrected day trims at exactly the boundary overtime
	already respects.
	"""
	if not (shift and attendance_date):
		return None
	start_time = frappe.db.get_value("Shift Type", shift, "start_time")
	if start_time is None:
		return None
	return datetime.combine(getdate(attendance_date), get_time(start_time))


def entered_break_minutes(shift, in_time, out_time, company=None) -> int:
	"""The unpaid break for a typed in/out pair, read from the SAME Shift Break
	rows the hourly job applies, so a corrected day and an automatic one agree.

	Weekday-aware by construction: the rows carry a day of week, so a Friday
	correction takes the prayer break too. No shift, no times, or no rows means
	nothing to deduct.
	"""
	if not (shift and in_time and out_time):
		return 0
	from hrms.utils.break_calculation import get_shift_break_minutes_for_intervals

	minutes = get_shift_break_minutes_for_intervals(
		shift, [(get_datetime(in_time), get_datetime(out_time))], company=company
	)
	logger.debug("[attendance] entered times on shift %s carry %s break minute(s)", shift, minutes)
	return minutes


def validate_attendance_times(in_time, out_time, attendance_date) -> None:
	"""What a person may type: both times or neither; out after in; within a day;
	in on the attendance date (a night shift ends the next morning)."""
	if not in_time and not out_time:
		return
	if not (in_time and out_time):
		frappe.throw(_("Enter both the in time and the out time, or neither."))
	start, end = get_datetime(in_time), get_datetime(out_time)
	if end <= start:
		frappe.throw(_("The out time must be after the in time."))
	if end - start > timedelta(hours=24):
		frappe.throw(_("In and out must be within 24 hours of each other."))
	if start.date() != getdate(attendance_date):
		frappe.throw(_("The in time must fall on the attendance date."))


def _times_differ(before, doc) -> bool:
	def _dt(value):
		return get_datetime(value) if value else None

	return _dt(before.in_time) != _dt(doc.in_time) or _dt(before.out_time) != _dt(doc.out_time)


def _clock(value) -> str:
	return get_datetime(value).strftime("%H:%M") if value else "—"


@frappe.whitelist()
def get_events(start: date | str, end: date | str, filters: str | list | None = None) -> list[dict]:
	employee = get_employee()
	if not employee:
		return []

	if isinstance(filters, str):
		import json

		filters = json.loads(filters)
	if not filters:
		filters = []
	filters.append(["attendance_date", "between", [get_datetime(start).date(), get_datetime(end).date()]])
	attendance_records = add_attendance(filters)
	add_holidays(attendance_records, start, end, employee)
	return attendance_records


def add_attendance(filters):
	attendance = frappe.get_list(
		"Attendance",
		fields=[
			"name",
			ValueWrapper("Attendance").as_("doctype"),
			"attendance_date",
			"employee_name",
			"status",
			"docstatus",
		],
		filters=filters,
	)
	for record in attendance:
		record["title"] = f"{record['employee_name']} : {record['status']}"
	return attendance


def add_holidays(events, start, end, employee=None):
	holidays = get_holidays_for_employee(employee, start, end)
	if not holidays:
		return

	for holiday in holidays:
		events.append(
			{
				"doctype": "Holiday",
				"attendance_date": holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name,
				"allDay": 1,
			}
		)


def mark_attendance(
	employee,
	attendance_date,
	status,
	shift=None,
	leave_type=None,
	late_entry=False,
	early_exit=False,
	half_day_status=None,
	auto_attendance=False,
):
	savepoint = "attendance_creation"

	try:
		frappe.db.savepoint(savepoint)
		attendance = frappe.new_doc("Attendance")
		attendance.update(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": attendance_date,
				"status": status,
				"shift": shift,
				"leave_type": leave_type,
				"late_entry": late_entry,
				"early_exit": early_exit,
				"half_day_status": half_day_status,
				# Marks automation ownership: a provisional Absent stamped here
				# is repairable in place when late check-ins arrive; a person's
				# manual Attendance never carries it, so it is never overwritten.
				"auto_attendance": 1 if auto_attendance else 0,
			}
		)
		attendance.insert()
		attendance.submit()
		logger.info(
			"[attendance] marked %s for %s on %s (auto=%s)",
			status,
			employee,
			attendance_date,
			bool(auto_attendance),
		)
	except (DuplicateAttendanceError, OverlappingShiftAttendanceError):
		frappe.db.rollback(save_point=savepoint)
		return

	return attendance.name


@frappe.whitelist()
def mark_bulk_attendance(data: str | dict):
	import json

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return
	if len(data.unmarked_days) > 10 or frappe.flags.test_bg_job:
		job_id = f"process_bulk_attendance_for_employee_{data.employee}"
		job = frappe.enqueue(
			process_bulk_attendance_in_batches, data=data, job_id=job_id, timeout=600, deduplicate=True
		)
		if job:
			message = _(
				"Bulk attendance marking is queued with a background job. It may take a while. You can monitor the job status {0}"
			).format(get_link_to_form("RQ Job", job.id, label="here"))
		else:
			message = _(
				"Bulk attendance marking is already in progress for employee {0}. You can monitor the job status {1}"
			).format(frappe.bold(data.employee), get_link_to_form("RQ Job", get_job(job_id).id, label="here"))
		frappe.msgprint(message, allow_dangerous_html=True)
	else:
		process_bulk_attendance_in_batches(data)
		frappe.msgprint(_("Attendance marked successfully."), alert=True)


def process_bulk_attendance_in_batches(data, chunk_size=20):
	savepoint = "mark_bulk_attendance"
	for days in create_batch(data.unmarked_days, chunk_size):
		for attendance_date in days:
			try:
				frappe.db.savepoint(savepoint)
				doc_dict = {
					"doctype": "Attendance",
					"employee": data.employee,
					"attendance_date": getdate(attendance_date),
					"status": data.status,
					"half_day_status": "Absent" if data.status == "Half Day" else None,
					"shift": data.shift,
				}
				attendance = frappe.get_doc(doc_dict).insert()
				attendance.submit()
			except (DuplicateAttendanceError, OverlappingShiftAttendanceError, Exception):
				if not frappe.flags.in_test:
					frappe.db.rollback(save_point=savepoint)
				continue
		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep


@frappe.whitelist()
def get_unmarked_days(
	employee: str, from_date: str | date, to_date: str | date, exclude_holidays: str | int = 0
) -> list:
	frappe.has_permission("Employee", "read", employee, throw=True)
	joining_date, relieving_date = frappe.get_cached_value(
		"Employee", employee, ["date_of_joining", "relieving_date"]
	)

	from_date = max(getdate(from_date), joining_date or getdate(from_date))
	to_date = min(getdate(to_date), relieving_date or getdate(to_date))

	records = frappe.get_all(
		"Attendance",
		fields=["attendance_date", "employee"],
		filters=[
			["attendance_date", ">=", from_date],
			["attendance_date", "<=", to_date],
			["employee", "=", employee],
			["docstatus", "!=", 2],
		],
	)

	marked_days = [getdate(record.attendance_date) for record in records]

	if cint(exclude_holidays):
		holiday_dates = get_holiday_dates_between_range(
			employee, from_date, to_date, raise_exception_for_holiday_list=False
		)
		holidays = [getdate(record) for record in holiday_dates]
		marked_days.extend(holidays)

	unmarked_days = []

	while from_date <= to_date:
		if from_date not in marked_days:
			unmarked_days.append(from_date)

		from_date = add_days(from_date, 1)

	return unmarked_days


@frappe.whitelist()
def get_employee_shift(employee: str, for_date: str | date | None = None) -> str | None:
	if not employee:
		return None

	if employee and not frappe.has_permission("Employee", "read", employee):
		return None

	if not for_date:
		for_date = nowdate()

	for_date = getdate(for_date)

	if not frappe.has_permission("Shift Assignment", "read"):
		return None

	shifts = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Active",
			"start_date": ("<=", for_date),
		},
		fields=["shift_type", "start_date"],
		order_by="start_date desc",
		limit=1,
	)

	if shifts:
		return shifts[0].shift_type

	default_shift = frappe.db.get_value("Employee", employee, "default_shift")
	if default_shift:
		return default_shift

	return None


def backfill_rows_to_write(rows, locked) -> tuple[list, list]:
	"""Split recomputed rows into (write, skipped). Pure.

	`locked` is {(employee, date-string)} where an approved OT request,
	replacement leave or a submitted payslip already depends on the day. Those
	are reported with their figures intact — HR needs to see what was left alone
	and what it would have become — and never written.
	"""
	write, skipped = [], []
	for row in rows:
		key = (row.get("employee"), str(row.get("date")))
		(skipped if key in locked else write).append(row)
	return write, skipped


def recompute_ot_backfill(from_date, to_date, dry_run=1):
	"""Recompute OT (ot_hours / ot_rate_weighted_hours / ot_rate_bands) for submitted
	Attendance in [from_date, to_date] using the corrected engine. dry_run=1 (default)
	only reports what WOULD change; pass dry_run=0 to write (submit-safe via db_set).
	Run: bench --site <site> execute
	hrms.hr.doctype.attendance.attendance.recompute_ot_backfill
	--kwargs "{'from_date':'2026-06-16','to_date':'2026-07-31','dry_run':1}\""""
	dry_run = cint(dry_run)
	logger.info("[attendance] OT backfill %s..%s dry_run=%s", from_date, to_date, dry_run)
	names = frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "attendance_date": ["between", [from_date, to_date]]},
		pluck="name",
	)
	changed, recomputed = [], {}
	for name in names:
		doc = frappe.get_doc("Attendance", name)
		old_hours, old_weighted = flt(doc.ot_hours), flt(doc.ot_rate_weighted_hours)
		doc.set_overtime()
		new_hours, new_weighted = flt(doc.ot_hours), flt(doc.ot_rate_weighted_hours)
		if new_hours == old_hours and new_weighted == old_weighted:
			continue
		changed.append(
			{
				"attendance": name,
				"employee": doc.employee,
				"date": str(doc.attendance_date),
				"old_ot_hours": old_hours,
				"new_ot_hours": new_hours,
				"old_rate_weighted": old_weighted,
				"new_rate_weighted": new_weighted,
			}
		)
		recomputed[name] = doc

	# A day a payout already depends on is HR's to correct by hand. The repair
	# tool beside this one has refused such days since it shipped; this one
	# rewrote them, which is why it was bench-only and never ran on deploy.
	locked = set()
	if not dry_run:
		from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

		for row in changed:
			if _repair_financial_dependency(row["employee"], row["date"], row["attendance"], for_update=True):
				locked.add((row["employee"], str(row["date"])))
	write, skipped = backfill_rows_to_write(changed, locked)

	if not dry_run:
		for row in write:
			doc = recomputed[row["attendance"]]
			doc.db_set("ot_hours", row["new_ot_hours"], update_modified=False)
			doc.db_set("ot_rate_weighted_hours", row["new_rate_weighted"], update_modified=False)
			for band in doc.ot_rate_bands:
				band.docstatus = doc.docstatus
			doc.update_child_table("ot_rate_bands")
		frappe.db.commit()
	for row in skipped:
		logger.warning(
			"[attendance] OT backfill left %s (%s on %s) alone: a payout depends on it; "
			"%s h would have become %s h",
			row["attendance"],
			row["employee"],
			row["date"],
			row["old_ot_hours"],
			row["new_ot_hours"],
		)
	logger.info(
		"[attendance] OT backfill done scanned=%d changed=%d written=%d locked=%d",
		len(names),
		len(changed),
		0 if dry_run else len(write),
		len(skipped),
	)
	return {
		"dry_run": bool(dry_run),
		"scanned": len(names),
		"changed": len(changed),
		"written": 0 if dry_run else len(write),
		"locked": len(skipped),
		"records": changed,
		"skipped": skipped,
	}
