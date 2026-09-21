# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import logging
from datetime import datetime, timedelta
from itertools import groupby, pairwise

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	now_datetime,
	time_diff,
)

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.setup.doctype.holiday_list.holiday_list import is_half_holiday, is_holiday

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
	worked_intervals,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_employee_shift,
	get_shift_details,
	has_overlapping_timings,
)
from hrms.utils import get_date_range
from hrms.utils.holiday_list import get_holiday_dates_between, holiday_list_covers
from hrms.utils.hr_removed_day import HR_REMOVED_DEVICE, hold_punches, removed_by_hr
from hrms.utils.leave_cover import request_covered_days
from hrms.utils.shift_resolution import SESSION_WINDOW

logger = logging.getLogger(__name__)

EMPLOYEE_CHUNK_SIZE = 50

#: Settings that decide which punches belong to the shift; changing any of
#: them under unmarked punches would re-read those punches differently.
WINDOW_FIELDS = (
	"start_time",
	"end_time",
	"begin_check_in_before_shift_start_time",
	"allow_check_out_after_shift_end_time",
)


def _clock_minutes(value) -> int:
	if isinstance(value, timedelta):
		return int(value.total_seconds() // 60)
	clock = get_time(value)
	return clock.hour * 60 + clock.minute


def _company_of_logs(logs) -> str | None:
	"""Company of the employee these check-in logs belong to.

	Used to resolve company-scoped policy (the Ramadan break window). All logs
	in a group belong to one employee by contract, so the first row decides.
	Returns None when it can't be resolved, which makes the resolver fall back
	to the global setting — i.e. the pre-multi-company behaviour.
	"""
	employee = logs[0].employee if logs else None
	if not employee:
		return None
	try:
		return frappe.get_cached_value("Employee", employee, "company")
	except Exception:
		logger.warning("[shift_type] Could not resolve company for employee %s", employee)
		return None


#: What the hourly job reads off a punch; linked_checkins reads the same so a
#: rebuilt day is computed from rows shaped exactly like fresh ones.
CHECKIN_FIELDS = (
	"name",
	"employee",
	"log_type",
	"time",
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"device_id",
	"overtime_type",
	"skip_auto_attendance",
	"remote_approval_status",
	"requires_remote_approval",
	"offshift",
	# which row a punch already belongs to: a failed rebuild must not silence
	# punches that were linked and fine before it ran
	"attendance",
)
#: Read alongside the rest, but only once the column exists. A SELECT naming a
#: column a site has not caught up with yet dies with "Unknown column" — this
#: fork has been bitten by exactly that (`ensure_extension_custom_fields`).
#: Absent from a row, `skipped_as_noise` reads as 0, which `splits_the_day`
#: treats as a WALL: the conservative answer, so that window behaves like the
#: code did before this field existed.
NOISE_FIELD = "skipped_as_noise"


def checkin_fields() -> list:
	"""CHECKIN_FIELDS, plus the noise verdict on sites that have the column."""
	if getattr(frappe.local, "_hrms_has_noise_field", None) is None:
		try:
			frappe.local._hrms_has_noise_field = bool(frappe.db.has_column("Employee Checkin", NOISE_FIELD))
		except Exception:
			logger.warning("[shift_type] could not check for %s; reading without it", NOISE_FIELD)
			frappe.local._hrms_has_noise_field = False
		if not frappe.local._hrms_has_noise_field:
			logger.warning(
				"[shift_type] Employee Checkin.%s is not on this site yet; every skipped punch "
				"reads as a wall until the column exists",
				NOISE_FIELD,
			)
	return [*CHECKIN_FIELDS, NOISE_FIELD] if frappe.local._hrms_has_noise_field else list(CHECKIN_FIELDS)


def get_automation_attendance(employee, attendance_date, shift):
	"""The submitted punch-owned Attendance for this shift day, or None.

	Never returned, so never rebuilt from punches: a row HR marked by hand
	(auto_attendance=0), one owned by the source instance, and a LEAVE row.
	A leave applied against an auto-marked Absent is converted in place and
	keeps auto_attendance=1, so the flag alone does not say who owns the row;
	leave_type, modify_half_day_status and the On Leave status do.

	A row marked before `shift` was reliably stamped is found on a second
	look with the shift unset, the tolerance the late-checkout repair has.
	"""
	base = {
		"employee": employee,
		"attendance_date": attendance_date,
		"docstatus": 1,
		"auto_attendance": 1,
		"synced_from_instance": ("is", "not set"),
		"leave_type": ("is", "not set"),
		"modify_half_day_status": 0,
		"status": ("!=", "On Leave"),
	}
	name = frappe.db.get_value("Attendance", {**base, "shift": shift}, "name") or frappe.db.get_value(
		"Attendance", {**base, "shift": ("is", "not set")}, "name"
	)
	if not name:
		# A provisional Absent another, overlapping shift's marker wrote for the
		# same day (no punch ever linked to it) is not evidence of a second shift
		# worked; the punches under this shift replace it. A row with linked
		# punches under the other shift is a real day and stays.
		for row in frappe.get_all(
			"Attendance", filters={**base, "shift": ("!=", shift)}, fields=["name", "shift"]
		):
			if not has_overlapping_timings(shift, row.shift):
				continue
			if frappe.db.exists("Employee Checkin", {"attendance": row.name}):
				continue
			logger.info(
				"[shift_type] provisional %s under overlapping shift %s will be rebuilt under %s",
				row.name,
				row.shift,
				shift,
			)
			name = row.name
			break
	return frappe.get_doc("Attendance", name) if name else None


def linked_checkins(attendance_name) -> list:
	"""The punches already linked to an Attendance, shaped like the job's rows."""
	return day_evidence({"attendance": attendance_name}, order_by="time")


def pending_late_checkouts(rows) -> set:
	"""Names of the rows that are forgotten check-outs still waiting for their
	approver (E16). One read of Remote Checkin Request, only for Pending rows.
	Employee Checkin carries no late-checkout flag; the request filed for it does."""
	pending = sorted({row.get("name") for row in rows if row.get("remote_approval_status") == "Pending"})
	if not pending:
		return set()
	late = {
		r.get("checkin")
		for r in frappe.get_all(
			"Remote Checkin Request",
			filters={"checkin": ["in", pending], "is_late_checkout": 1, "status": "Pending"},
			fields=["checkin"],
			limit_page_length=0,
		)
	} & set(pending)
	if late:
		logger.info("[shift_type] %d pending late check-out(s) wait for approval", len(late))
	return late


def day_evidence(filters, order_by="time") -> list:
	"""The Employee Checkin rows the engine must see, whoever asks. ONE loader.

	Callers say WHICH punches (a shift's unlinked window, one employee-day, the
	rows linked to an Attendance); this says what every reading has in common:

	* the full field list, `skipped_as_noise` included, so `attendance_segments`
	  can tell a wall from noise;
	* a skipped or rejected punch is KEPT — it is a wall that separates two
	  spans, and dropping it here bridged time the approver had rejected
	  (21 Sep 2026 audit, E-H1: the hourly job kept it, both re-mark paths
	  dropped it, and the same day flipped between Half Day and Present);
	* a mirrored punch is left to the instance that owns it (single writer,
	  hrms/sync/write_block.py);
	* a forgotten check-out still Pending is a claim, not evidence (E16): it is
	  left out and its approval rebuilds the day.
	"""
	mirrored = ("synced_from_instance", "is", "not set")
	if isinstance(filters, dict):
		filters = {**filters, mirrored[0]: mirrored[1:]}
	else:
		filters = [*filters, list(mirrored)]
	rows = frappe.get_all(
		"Employee Checkin",
		fields=checkin_fields(),
		filters=filters,
		order_by=order_by,
		limit_page_length=0,
	)
	late = pending_late_checkouts(rows)
	for row in rows:
		row["is_late_checkout"] = 1 if row.get("name") in late else 0
	logger.debug("[shift_type] day_evidence: %d row(s), %d pending late check-out(s)", len(rows), len(late))
	return [row for row in rows if not row["is_late_checkout"]]


def paid_intervals_from(intervals, shift_start) -> tuple[list, float]:
	"""The worked intervals trimmed to begin no earlier than the shift, and the
	hours that trimming removed. Pure.

	Only the part before the start goes, never the whole interval: an employee
	who arrives at 07:30 and works to 18:05 is paid 09:00 to 18:05, not nothing.

	Returning the trimmed intervals as well as the number is what keeps break
	deduction honest — a break configured before the shift starts must not be
	taken off hours that were never counted in the first place, and it would be
	if the breaks were still measured against the untrimmed span.
	"""
	if not shift_start:
		return list(intervals), 0.0
	shift_start = get_datetime(shift_start)
	paid, removed = [], 0.0
	for start, end in intervals:
		start, end = get_datetime(start), get_datetime(end)
		if end <= shift_start:
			removed += (end - start).total_seconds() / 3600
			continue
		if start < shift_start:
			removed += (shift_start - start).total_seconds() / 3600
			start = shift_start
		paid.append((start, end))
	return paid, round(removed, 6)


def counts_for_attendance(row) -> bool:
	"""A punch that is evidence for attendance STATUS and hours.

	Wider than overtime's `_is_eligible_checkin` on purpose. A punch still
	waiting for its approver is provisional presence, not absence: the day
	reads Present now and is corrected if the approver rejects. Applying the
	overtime rule here (8 Sep, ae0028f30) auto-marked every employee whose
	check-in was out of radius as Absent and split First/Last spans into Half
	Days while the request sat in the approver's queue. A REJECTED punch
	(rejection sets skip_auto_attendance), an off-shift punch and a skipped
	one are not evidence. Overtime keeps the strict rule: unverified minutes
	are never paid.
	"""
	return (
		not cint(row.get("skip_auto_attendance") or 0)
		and not cint(row.get("offshift") or 0)
		and row.get("remote_approval_status") != "Rejected"
		# E16 (15 Sep 2026): a forgotten check-out filed late is a CLAIM until its
		# approver says yes. Counting it while Pending marked the day Present and
		# a later reject left it so; approval rebuilds the day through
		# reprocess_late_checkout_attendance, so nothing is lost by waiting.
		and not (row.get("remote_approval_status") == "Pending" and cint(row.get("is_late_checkout") or 0))
	)


def splits_the_day(row) -> bool:
	"""A punch that separates two spans and must never be bridged across. Pure.

	Not the same question as `counts_for_attendance`. Both a REJECTED punch and
	a tap HR ignored are "not evidence", but only the first is a WALL: bridging
	across time nobody verified would pay it. A tap judged NOISE is simply not
	there, and the taps on either side of it are one session — which is what
	ignoring a tap means.

	The default is the WALL, and that is the whole safety of this rule. A punch
	has to be ticked `skipped_as_noise` by the code that judged it noise — Fix
	Day's ignore and rebuild, and the burst-tap stutter — to be read across.
	Everything else that does not count keeps the old, conservative behaviour,
	including anything a future writer adds and, specifically, the punches
	`handle_attendance_exception` skip-stamps when a rebuild is refused by the
	financial guard: the system DEFERRED those, nobody judged them (found in
	review of ff1493e85, which had inverted this and would have bridged them).

	Live, 17 Sep 2026: Norazlin's 4 September had its accidental mid-day OUT and
	its 16-second glitch burst ignored, and the two real taps then sat in two
	one-tap segments and never paired. The day read "in 09:03 · out — · 0 h".
	"""
	if counts_for_attendance(row):
		return False
	return not cint(row.get("skipped_as_noise") or 0)


def attendance_segments(logs) -> list:
	"""The day's logs as contiguous runs of evidence, split only at a wall. Pure.

	An ignored tap is dropped before grouping, so it cannot separate the taps
	around it; `splits_the_day` rows stay in place and do separate them. Each
	segment is then given to the shift's own configured calculation, so the
	native first-in/last-out or alternating pairing is preserved WITHIN a span
	and never across a wall.
	"""
	usable = [row for row in logs if counts_for_attendance(row) or splits_the_day(row)]
	spans = [list(group) for eligible, group in groupby(usable, key=counts_for_attendance) if eligible]
	return [part for span in spans for part in _cut_overlong_sessions(span)]


def _cut_overlong_sessions(span) -> list:
	"""A session longer than SESSION_WINDOW is cut (owner's rule, 21 Sep 2026). Pure.

	An OUT more than 20 h after the IN it would close is not that IN's closer:
	the IN is left open (missing clock-out) and the OUT starts its own span (a
	lone OUT, missing clock-in). `choose_shift` applies the same window at tap
	time; this is for the punches that reach the engine stamped on one shift by
	an import or a re-stamp, which a 23-hour "Present" came from.
	"""
	parts, current, open_in = [], [], None
	for row in span:
		moment, log_type = get_datetime(row.get("time")), row.get("log_type")
		if log_type == "OUT" and open_in is not None and moment - open_in > SESSION_WINDOW:
			logger.info(
				"[shift_type] %s is %s after its IN — the session is cut", row.get("name"), moment - open_in
			)
			parts.append(current)
			current, open_in = [], None
		current.append(row)
		if log_type == "IN":
			open_in = moment if open_in is None else open_in
		elif log_type == "OUT":
			open_in = None
	parts.append(current)
	return [part for part in parts if part]


class ShiftType(Document):
	def validate(self):
		start = get_time(self.start_time)
		end = get_time(self.end_time)
		self.validate_same_start_and_end(start, end)
		self.validate_circular_shift(start, end)
		self.validate_unlinked_logs()
		self.warn_about_buffers()
		self.warn_about_mode_mix()
		self.validate_overtime_rates()
		self.seed_last_sync_of_checkin()
		logger.debug("[shift_type] validated %s", self.name)

	# Shift definitions are HR's (D5): the two checks below only WARN.

	def warn_about_buffers(self):
		"""A check-in/out buffer longer than the shift, or over two hours,
		pulls punches from far outside the shift onto it — where they meet
		another shift's window (F1/F16). Reported, never changed."""
		start, end = _clock_minutes(self.start_time), _clock_minutes(self.end_time)
		length = end - start if end > start else end + 1440 - start
		for label, value in (
			(_("Begin check-in before shift start time"), cint(self.begin_check_in_before_shift_start_time)),
			(_("Allow check-out after shift end time"), cint(self.allow_check_out_after_shift_end_time)),
		):
			if value > length:
				msg = _(
					"{0} is {1} minutes, longer than the shift itself ({2} minutes). Punches that far "
					"outside the shift are read as this shift's. Nothing was changed — please check it."
				).format(frappe.bold(label), value, length)
			elif value > 120:
				msg = _(
					"{0} is {1} minutes, more than 120. Punches up to {1} minutes outside the shift are "
					"read as this shift's and may meet another shift. Nothing was changed — please check it."
				).format(frappe.bold(label), value)
			else:
				continue
			logger.warning("[shift_type] %s: %s = %d min (shift %d min)", self.name, label, value, length)
			frappe.msgprint(msg, title=_("Check the buffer"), indicator="orange")

	def warn_about_mode_mix(self):
		"""Alternating IN/OUT pairing with first-in/last-out hours pays the
		mid-day gap as hours while overtime ignores it (F15). Reported only."""
		alternating = self.determine_check_in_and_check_out == (
			"Alternating entries as IN and OUT during the same shift"
		)
		first_last = self.working_hours_calculation_based_on == "First Check-in and Last Check-out"
		if not (alternating and first_last):
			return
		logger.warning("[shift_type] %s: alternating pairing with first/last hours", self.name)
		frappe.msgprint(
			_(
				"Check-ins are paired as alternating IN and OUT, but hours are counted from the first "
				"check-in to the last check-out. A mid-day gap (out and back in) is paid as working "
				"hours while overtime leaves it out. Nothing was changed — choose {0} if the gap "
				"should not be paid."
			).format(frappe.bold(_("Every Valid Check-in and Check-out"))),
			title=_("Hours and overtime read the day differently"),
			indicator="orange",
		)

	def seed_last_sync_of_checkin(self):
		# Auto mode needs a concrete baseline: with last_sync_of_checkin empty,
		# has_incorrect_shift_config() skips the shift entirely and the hourly
		# advance only recovers after the next shift end passes — so ticking
		# auto_update_last_sync on an empty value would process nothing.
		# Server-side so API writes behave the same as form saves.
		if self.auto_update_last_sync and not self.last_sync_of_checkin:
			self.last_sync_of_checkin = now_datetime()
			logger.info(
				"[shift_type] %s: seeded last_sync_of_checkin (auto update on, value was empty)",
				self.name,
			)
			frappe.msgprint(
				_("Last Sync of Checkin was empty and has been set to {0}.").format(
					frappe.bold(self.last_sync_of_checkin)
				),
				alert=True,
				indicator="blue",
			)

	def validate_same_start_and_end(self, start_time: datetime.time, end_time: datetime.time):
		if start_time == end_time:
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Start time and end time cannot be same."),
			)

	def validate_circular_shift(self, start_time: datetime.time, end_time: datetime.time):
		shift_start, shift_end = self.get_shift_start_and_shift_end(start_time, end_time)
		if self.get_total_shift_duration_in_minutes(shift_start, shift_end) >= 1440:
			max_label = self.get_max_shift_buffer_label()
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Please reduce {0} to avoid shift time overlapping with itself").format(
					frappe.bold(max_label)
				),
			)

	def get_shift_start_and_shift_end(
		self, start_time: datetime.time, end_time: datetime.time
	) -> tuple[datetime]:
		shift_start = datetime.combine(getdate(), start_time)
		if start_time < end_time:
			shift_end = datetime.combine(getdate(), end_time)
		elif start_time > end_time:
			shift_end = datetime.combine(add_days(getdate(), 1), end_time)
		return shift_start, shift_end

	def get_total_shift_duration_in_minutes(
		self, shift_start: datetime.time, shift_end: datetime.time
	) -> int:
		return (
			(round(time_diff(shift_end, shift_start).total_seconds() / 60))
			+ (self.allow_check_out_after_shift_end_time or 0)
			+ (self.begin_check_in_before_shift_start_time or 0)
		)

	def get_max_shift_buffer_label(self) -> str:
		labels = {
			_(
				self.meta.get_label("allow_check_out_after_shift_end_time")
			): self.allow_check_out_after_shift_end_time,
			_(
				self.meta.get_label("begin_check_in_before_shift_start_time")
			): self.begin_check_in_before_shift_start_time,
		}
		return max(labels, key=labels.get)

	def validate_unlinked_logs(self):
		if self.is_new():
			return
		changed = [field for field in WINDOW_FIELDS if self.has_value_changed(field)]
		if changed and self.unlinked_checkins_exist():
			logger.warning("[shift_type] %s: %s changed with unmarked punches — refused", self.name, changed)
			frappe.throw(
				title=_("Unmarked Check-in Logs Found"),
				msg=_("Mark attendance for existing check-in/out logs before changing shift settings"),
			)

	def is_field_modified(self, fieldname):
		return not self.is_new() and self.has_value_changed(fieldname)

	def unlinked_checkins_exist(self):
		return frappe.db.exists(
			"Employee Checkin",
			{"shift": self.name, "attendance": ["is", "not set"], "skip_auto_attendance": 0, "offshift": 0},
		)

	def validate_overtime_rates(self):
		if not self.enable_overtime:
			return

		# seed Employment Act defaults only when overtime is first turned on,
		# so an intentionally-cleared table stays empty
		if not self.overtime_rates:
			if self.is_new() or self.has_value_changed("enable_overtime"):
				self.set_default_overtime_rates()
			return

		rows_by_type = {}
		for row in self.overtime_rates:
			from_min = (row.from_hour or 0) * 60 + (row.from_minute or 0)
			to_min = (row.to_hour or 0) * 60 + (row.to_minute or 0)
			if to_min <= from_min:
				frappe.throw(
					_("Row #{0}: {1} must be later than {2}").format(
						row.idx, frappe.bold(_("To")), frappe.bold(_("From"))
					)
				)
			rows_by_type.setdefault(row.day_type, []).append((from_min, to_min, row.idx))

		# bands for a day type must be contiguous from 0: no gaps, no overlaps, so
		# the engine never silently drops paid overtime between two bands
		for day_type, rows in rows_by_type.items():
			rows.sort()
			if rows[0][0] != 0:
				frappe.throw(
					_("{0}: the first overtime band must start at 0").format(frappe.bold(_(day_type))),
					title=_("Invalid Overtime Rates"),
				)
			for (_pf, prev_to, prev_idx), (cur_from, _ct, cur_idx) in pairwise(rows):
				if cur_from < prev_to:
					frappe.throw(
						_("Row #{0}: Overtime hour range overlaps with row #{1}").format(cur_idx, prev_idx),
						title=_("Overlapping Overtime Rates"),
					)
				if cur_from > prev_to:
					frappe.throw(
						_("Row #{0}: Overtime hour range leaves a gap after row #{1}").format(
							cur_idx, prev_idx
						),
						title=_("Non-continuous Overtime Rates"),
					)

	def set_default_overtime_rates(self):
		from hrms.utils.ot_calculation import DEFAULT_OT_RATE_BANDS

		for day_type, bands in DEFAULT_OT_RATE_BANDS.items():
			for from_hour, from_minute, to_hour, to_minute, rate in bands:
				self.append(
					"overtime_rates",
					{
						"day_type": day_type,
						"from_hour": from_hour,
						"from_minute": from_minute,
						"to_hour": to_hour,
						"to_minute": to_minute,
						"rate": rate,
					},
				)

	@frappe.whitelist()
	def process_auto_attendance(self, is_manually_triggered: int | bool = False) -> None | str:
		if self.has_incorrect_shift_config():
			return

		logs = self.get_employee_checkins()
		if is_manually_triggered:
			if len(logs) > 1000 or frappe.flags.test_bg_job:
				job_id = "process_auto_attendance_" + self.name
				job = frappe.enqueue(self._process, logs=logs, timeout=1200, job_id=job_id, deduplicate=True)
				return f"Attendance marking has been queued. It may take a few minutes. You can monitor the job status {get_link_to_form('RQ Job', job.id, label='here')}"
			else:
				try:
					self._process(logs)
					return "Attendance has been marked as per employee check-ins."
				except Exception as e:
					error_log = frappe.log_error(e)
					return f"An error occured during marking attendance. Refer the full error log {get_link_to_form('Error Log', error_log.name, label='here')}"
		else:
			self._process(logs)

	def has_incorrect_shift_config(self):
		return (
			not cint(self.enable_auto_attendance)
			or not self.process_attendance_after
			or not self.last_sync_of_checkin
		)

	def _process(self, logs):
		group_key = lambda x: (x["employee"], x["shift_start"])  # noqa
		for key, group in groupby(sorted(logs, key=group_key), key=group_key):
			lock_employee_row(key[0])
			self.mark_attendance_for_shift_logs(key[0], key[1].date(), list(group))
			# Commit per employee: releases that person's row lock at once, so
			# the nightly recovery and HR's master edit wait for one person, not
			# for the whole shift type's pass (E35). Progress is kept either way.
			if not frappe.in_test:
				frappe.db.commit()  # nosemgrep

		assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)
		# mark absent in batches & commit to avoid losing progress since this tries to process remaining attendance
		# right from "Process Attendance After" to "Last Sync of Checkin"
		for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
			for employee in batch:
				self.mark_absent_for_dates_with_no_attendance(employee)
				self.mark_absent_for_half_day_dates(employee)

			if not frappe.in_test:
				frappe.db.commit()  # nosemgrep

	def mark_attendance_for_shift_logs(
		self, employee, attendance_date, single_shift_logs, repair_attendance=None
	):
		"""Mark one employee's attendance for one shift day from its check-ins.

		The single rule the hourly job and the late check-out approval share
		(hrms.overrides.remote_checkin_request_hooks.reprocess_late_checkout_attendance):
		one implementation, so a threshold change here reaches both.
		Returns the Attendance, or None when the day is not to be marked.

		A day HR removed in Shift Attendance is never marked: its new punches
		are held (skip-stamped with the editor's marker) so they are not read
		again every hour and hand_back releases them.
		"""
		if removed_by_hr(employee, attendance_date):
			held = [
				row.name
				for row in single_shift_logs
				if not row.get("attendance") and counts_for_attendance(row)
			]
			if held:
				hold_punches(held, attendance_date)
			logger.info("[shift_type] %s on %s was removed by HR: not marked", employee, attendance_date)
			return None
		# Through the class, not `self`: callers (and test_pending_punch_attendance)
		# run this unbound on a plain object carrying only the Shift Type's fields.
		day = ShiftType.shift_day_result(self, employee, attendance_date, single_shift_logs)
		if day is None:
			return None
		logger.debug(
			"[shift_type] marking %s on %s under %s: %s", employee, attendance_date, self.name, day.status
		)
		return mark_attendance_and_link_log(
			day.eligible_logs,
			day.status,
			attendance_date,
			day.working_hours,
			day.late_entry,
			day.early_exit,
			day.in_time,
			day.out_time,
			self.name,
			day.overtime_type,
			repair_attendance=repair_attendance,
			existing_attendance=day.existing,
		)

	def shift_day_result(self, employee, attendance_date, single_shift_logs):
		"""What marking one shift day from these check-ins would produce. Reads only.

		The computing half of `mark_attendance_for_shift_logs`, split out so a
		preview (`hrms.sync.checkin_import.remark_attendance`, dry run) reports
		exactly what the job would write rather than a second copy of the rule.
		None when the day is not to be marked; otherwise the automation row the
		marking would rebuild (`existing`), the punches it would link
		(`eligible_logs`) and the result.
		"""
		from hrms.utils.ot_calculation import _classify_day, _is_eligible_checkin, _pair_sessions

		if _classify_day(employee, attendance_date, "normal", shift=self.name) != "normal":
			if not _pair_sessions(single_shift_logs, {self.name: self.determine_check_in_and_check_out}):
				logger.info("[shift_type] no eligible holiday pair; attendance not created")
				return None
		# A day marked earlier from part of its evidence (a pending punch was left
		# unlinked between 8 Sep and the rule fix, or a punch was approved after
		# the marking) is rebuilt from ALL its punches, not collided with.
		existing = get_automation_attendance(employee, attendance_date, self.name)
		if existing is not None:
			seen = {row.name for row in single_shift_logs}
			single_shift_logs = sorted(
				[
					*single_shift_logs,
					*[row for row in linked_checkins(existing.name) if row.name not in seen],
				],
				key=lambda row: get_datetime(row.time),
			)
			logger.info(
				"[shift_type] %s already marks %s on %s — recomputing from %d punch(es)",
				existing.name,
				employee,
				attendance_date,
				len(single_shift_logs),
			)

		# Attendance evidence, not overtime evidence: a pending punch counts.
		eligible_logs = [row for row in single_shift_logs if counts_for_attendance(row)]
		if not eligible_logs:
			return None
		if not self.should_mark_attendance(employee, attendance_date):
			return None

		working_hours_threshold_for_half_day = flt(self.working_hours_threshold_for_half_day)
		working_hours_threshold_for_absent = flt(self.working_hours_threshold_for_absent)

		if self.is_half_holiday(employee, attendance_date):
			working_hours_threshold_for_half_day = flt(self.working_hours_threshold_for_half_day) / 2
			working_hours_threshold_for_absent = flt(self.working_hours_threshold_for_absent) / 2

		overtime_type = eligible_logs[0].get("overtime_type")
		day = self.get_attendance(
			single_shift_logs, working_hours_threshold_for_absent, working_hours_threshold_for_half_day
		)
		if day is None:
			# an open day (no IN→OUT pair): nothing to write, HR closes it
			return None
		(
			attendance_status,
			working_hours,
			late_entry,
			early_exit,
			in_time,
			out_time,
		) = day

		return frappe._dict(
			existing=existing,
			eligible_logs=eligible_logs,
			status=attendance_status,
			working_hours=working_hours,
			late_entry=late_entry,
			early_exit=early_exit,
			in_time=in_time,
			out_time=out_time,
			overtime_type=overtime_type,
		)

	def is_half_holiday(self, employee, attendance_date):
		holiday_list = self.get_holiday_list(employee, attendance_date)
		if is_half_holiday(holiday_list, attendance_date):
			return True
		return False

	def get_employee_checkins(self) -> list[dict]:
		return day_evidence(
			{
				"attendance": ("is", "not set"),
				"time": (">=", self.process_attendance_after),
				"shift_actual_end": ("<", self.last_sync_of_checkin),
				"shift": self.name,
				# Mirrored punches are owned by their source instance
				# (single-writer, hrms/sync/write_block.py). `day_evidence`
				# excludes them for every reader; named here as well so the
				# hub-writer audit (test_leave_rules) sees it at this site.
				"synced_from_instance": ("is", "not set"),
			},
			order_by="employee,time",
		)

	def get_attendance(self, logs, working_hours_threshold_for_absent, working_hours_threshold_for_half_day):
		"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
		for a set of logs belonging to a single shift — or None when the day is OPEN.
		Assumptions:
		1. These logs belong to a single shift and employee; holidays use eligible pairs.
		2. Logs are in chronological order

		An open day is one with punches but no complete IN→OUT pair: a lone IN
		is "missing clock-out", a lone OUT is "missing clock-in" (owner's rule,
		21 Sep 2026). It is not Absent 0 h and it is not a status of its own:
		the engine writes nothing, HR's exception filter sees the day first, and
		payroll's unmarked-day setting decides it if nobody does.
		"""
		from hrms.utils.ot_calculation import _classify_day, _is_eligible_checkin, _pair_sessions

		if (
			logs
			and _classify_day(
				logs[0].employee, getdate(logs[0].shift_start or logs[0].time), "normal", shift=self.name
			)
			!= "normal"
		):
			intervals = _pair_sessions(logs, {self.name: self.determine_check_in_and_check_out})
			if intervals:
				hours = sum((row["last_out"] - row["first_in"]).total_seconds() for row in intervals) / 3600
				logger.debug("[shift_type] eligible holiday work is Present without weekday deductions")
				return "Present", hours, False, False, intervals[0]["first_in"], intervals[-1]["last_out"]
			# a lone punch on a holiday is an open day too, never Absent 0 h
			logger.info("[shift_type] holiday with %d punch(es) but no eligible pair — left open", len(logs))
			return None
		late_entry = early_exit = False
		# Preserve the configured native calculation within each contiguous
		# eligible segment. An invalid boundary never joins the surrounding
		# first-IN/last-OUT span, even with the First/Last working-hours policy.
		pairing = self.determine_check_in_and_check_out
		policy = self.working_hours_calculation_based_on
		segments = attendance_segments(logs)
		parts = [calculate_working_hours(segment, pairing, policy) for segment in segments]
		total_working_hours = sum(part[0] for part in parts)
		in_time = next((part[1] for part in parts if part[1]), None)
		out_time = next((part[2] for part in reversed(parts) if part[2]), None)
		# Breaks are deducted where the time was worked, not against the
		# first-IN/last-OUT span: the pairs here are the pairs the hours came from.
		intervals = [
			(get_datetime(start), get_datetime(end))
			for segment in segments
			for start, end in worked_intervals(segment, pairing, policy)
		]
		if not intervals:
			logger.info(
				"[shift_type] %s on %s: %d punch(es) but no IN→OUT pair — the day is left open for HR",
				logs[0].employee,
				getdate(logs[0].shift_start or logs[0].time),
				len(logs),
			)
			return None
		# Arriving early is presence, not paid work: the day's hours start when
		# the shift starts. The check-in keeps its real time on the punch and in
		# In Time, so HR still sees 07:30; only the hours begin at 09:00. HR's
		# ruling, 10 Sep 2026: "early clock in didnt counted as paid. they are
		# just safer, when their shift start that is the real clocked working
		# hours." Overtime already ignores early arrival (_ot_window_begin).
		intervals, unpaid_early = paid_intervals_from(intervals, logs[0].shift_start)
		total_working_hours -= unpaid_early
		total_working_hours = self._deduct_unpaid_breaks(
			total_working_hours, intervals, company=_company_of_logs(logs)
		)
		if (
			cint(self.enable_late_entry_marking)
			and in_time
			and in_time > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period))
		):
			late_entry = True

		if (
			cint(self.enable_early_exit_marking)
			and out_time
			and out_time < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period))
		):
			early_exit = True

		if working_hours_threshold_for_absent and total_working_hours < working_hours_threshold_for_absent:
			return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time

		if (
			working_hours_threshold_for_half_day
			and total_working_hours < working_hours_threshold_for_half_day
		):
			return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time

		return "Present", total_working_hours, late_entry, early_exit, in_time, out_time

	def _deduct_unpaid_breaks(self, total_working_hours, intervals, company=None):
		"""Subtract configured unpaid breaks from working hours.

		`intervals` are the (start, end) pairs the hours were counted from. A
		fixed window is deducted only where it overlaps them, so a worker who
		logs out for lunch is not deducted twice and an unrelated logout
		elsewhere in the day cannot hide the lunch. `company` selects whose
		Ramadan window applies — see hrms.utils.company_settings.
		"""
		if not intervals or not getattr(self, "breaks", None):
			return total_working_hours

		from hrms.utils.break_calculation import get_shift_break_minutes_for_intervals

		break_min = get_shift_break_minutes_for_intervals(self.name, intervals, company=company)
		if break_min <= 0:
			return total_working_hours
		return max(0.0, total_working_hours - break_min / 60.0)

	def mark_absent_for_dates_with_no_attendance(self, employee: str):
		"""Marks Absents for the given employee on working days in this shift that have no attendance marked.
		The Absent status is marked starting from 'process_attendance_after' or employee creation date.
		"""
		start_time = get_time(self.start_time)
		dates = self.get_dates_for_attendance(employee)

		for date in dates:
			timestamp = datetime.combine(date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)

			if shift_details and shift_details.shift_type.name == self.name:
				attendance = mark_attendance(employee, date, "Absent", self.name, auto_attendance=True)

				if not attendance:
					continue

				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Comment",
						"reference_doctype": "Attendance",
						"reference_name": attendance,
						"content": frappe._("Employee was marked Absent due to missing Employee Checkins."),
					}
				).insert(ignore_permissions=True)

	def get_dates_for_attendance(self, employee: str) -> list[str]:
		start_date, end_date = self.get_start_and_end_dates(employee)

		# no shift assignment found, no need to process absent attendance records
		if start_date is None:
			return []

		date_range = get_date_range(start_date, end_date)

		# skip marking absent on holidays
		holiday_list = self.get_holiday_list(employee)
		holiday_dates = get_holiday_dates_between(holiday_list, start_date, end_date)
		# skip dates with attendance
		marked_attendance_dates = self.get_marked_attendance_dates_between(employee, start_date, end_date)
		# "Absent for missing check-ins" means no check-ins AT ALL. With two
		# overlapping assignments, this shift's marker used to write Absent for a
		# day the employee punched under the other one; the real marking then
		# failed as an overlap and the punches were stamped skip.
		punched_dates = self.get_dates_with_checkins(employee, start_date, end_date)
		# Owner ruling (15 Sep 2026): a day a Leave Application or Attendance
		# Request speaks for — approved OR still awaiting a decision — is never
		# resolved to Absent by the automation. An open leave has no Attendance
		# row yet, so "dates with attendance" alone let the marker through.
		held_dates = request_covered_days(employee, start_date, end_date)
		if held_dates:
			logger.info(
				"[shift_type] %s: %d day(s) held from Absent marking by a leave or attendance request",
				employee,
				len(held_dates),
			)

		return sorted(
			set(date_range)
			- set(holiday_dates)
			- set(marked_attendance_dates)
			- set(punched_dates)
			- set(held_dates)
		)

	def get_dates_with_checkins(self, employee: str, start_date, end_date) -> list:
		"""Shift days this employee punched on, rejections excluded.

		A punch under this shift, under no shift, or under a shift whose timings
		overlap this one means the day was worked and must not be marked Absent
		here. A punch under a genuinely separate shift (morning vs night) is that
		shift's business. The day is the shift day, so a night shift's OUT after
		midnight does not protect the next calendar day.

		A day HR removed in Shift Attendance carries a marker punch; it protects
		its day under every shift, whatever that punch's stamp.
		"""
		rows = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": employee,
				"time": ("between", [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]),
				"remote_approval_status": ("!=", "Rejected"),
			},
			fields=["time", "shift_start", "shift", "device_id"],
		)
		days = set()
		for row in rows:
			if row.get("device_id") == HR_REMOVED_DEVICE:
				days.add(getdate(row.get("time")))
				continue
			shift = row.get("shift")
			if shift and shift != self.name and not has_overlapping_timings(self.name, shift):
				continue
			days.add(getdate(row.get("shift_start") or row.get("time")))
		return sorted(days)

	def get_start_and_end_dates(self, employee):
		"""Returns start and end dates for checking attendance and marking absent
		return: start date = max of `process_attendance_after` and DOJ
		return: end date = min of shift before `last_sync_of_checkin` and Relieving Date
		"""
		date_of_joining, relieving_date, employee_creation = frappe.get_cached_value(
			"Employee", employee, ["date_of_joining", "relieving_date", "creation"]
		)

		if not date_of_joining:
			date_of_joining = employee_creation.date()

		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		end_date = None

		shift_details = get_shift_details(self.name, get_datetime(self.last_sync_of_checkin))
		last_shift_time = (
			shift_details.actual_end if shift_details else get_datetime(self.last_sync_of_checkin)
		)

		# check if shift is found for 1 day before the last sync of checkin
		# absentees are auto-marked 1 day after the shift to wait for any manual attendance records
		prev_shift = get_employee_shift(employee, last_shift_time - timedelta(days=1), True, "reverse")
		if prev_shift and prev_shift.shift_type.name == self.name:
			end_date = (
				min(prev_shift.start_datetime.date(), relieving_date)
				if relieving_date
				else prev_shift.start_datetime.date()
			)
		else:
			# no shift found
			return None, None
		return start_date, end_date

	def get_marked_attendance_dates_between(self, employee: str, start_date: str, end_date: str) -> list[str]:
		Attendance = frappe.qb.DocType("Attendance")
		return (
			frappe.qb.from_(Attendance)
			.select(Attendance.attendance_date)
			.where(
				(Attendance.employee == employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date.between(start_date, end_date))
				& ((Attendance.shift.isnull()) | (Attendance.shift == self.name))
			)
		).run(pluck=True)

	def get_assigned_employees(self, from_date: datetime.date, consider_default_shift=False) -> list[str]:
		"""Get all such employees who either have this shift assigned that hasn't ended or have this shift as default shift.
		This may fetch some redundant employees who have another shift assigned that may have started or ended before or after the
		attendance processing date. But this is done to avoid missing any employee who may have this shift as active shift."""
		filters = {"shift_type": self.name, "docstatus": "1", "status": "Active"}

		or_filters = [["end_date", ">=", from_date], ["end_date", "is", "not set"]]

		assigned_employees = frappe.get_all(
			"Shift Assignment", filters=filters, or_filters=or_filters, pluck="employee"
		)

		if consider_default_shift:
			default_shift_employees = frappe.get_all(
				"Employee", filters={"default_shift": self.name, "status": "Active"}, pluck="name"
			)
			assigned_employees = set(assigned_employees + default_shift_employees)

		# exclude inactive employees
		inactive_employees = frappe.db.get_all("Employee", {"status": "Inactive"}, pluck="name")

		return list(set(assigned_employees) - set(inactive_employees))

	def get_holiday_list(self, employee: str, date=None) -> str:
		"""The calendar for `employee` on `date`: the shift's own while it
		covers the date, else the dated assignment. Without a date (the
		absent-marking range) the shift's own calendar is taken as before."""
		if self.holiday_list and (date is None or holiday_list_covers(self.holiday_list, date)):
			return self.holiday_list
		return get_holiday_list_for_employee(employee, False, as_on=date) or self.holiday_list

	def should_mark_attendance(self, employee: str, attendance_date: str) -> bool:
		"""Determines whether attendance should be marked on holidays or not"""
		from hrms.utils.ot_calculation import _classify_day

		# HR requires actual nonworking-day work to be recorded regardless of
		# this scheduling checkbox. The marking path requires an eligible pair;
		# incomplete holiday evidence never creates an automatic absence.
		if _classify_day(employee, attendance_date, "normal", shift=self.name) != "normal":
			return True
		if self.mark_auto_attendance_on_holidays:
			# no need to check if date is a holiday or not
			# since attendance should be marked on all days
			return True

		holiday_list = self.get_holiday_list(employee, attendance_date)
		if is_holiday(holiday_list, attendance_date):
			return False
		return True

	def mark_absent_for_half_day_dates(self, employee):
		half_day_attendances = frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"status": "Half Day",
				"modify_half_day_status": 1,
				"attendance_date": ["<=", getdate(self.last_sync_of_checkin)],
			},
			fields=["name", "attendance_date"],
		)
		start_time = get_time(self.start_time)
		for attendance in half_day_attendances:
			timestamp = datetime.combine(attendance.attendance_date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)
			if shift_details and shift_details.shift_type.name == self.name:
				frappe.db.set_value(
					"Attendance",
					attendance.name,
					{"shift": self.name, "half_day_status": "Absent", "modify_half_day_status": 0},
				)
				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Comment",
						"reference_doctype": "Attendance",
						"reference_name": attendance.name,
						"content": frappe._(
							"Employee was marked Absent for other half due to missing Employee Checkins."
						),
					}
				).insert(ignore_permissions=True)


def update_last_sync_of_checkin():
	"""Called from hooks"""
	shifts = frappe.get_all(
		"Shift Type",
		filters={"enable_auto_attendance": 1, "auto_update_last_sync": 1},
		fields=["name", "last_sync_of_checkin", "start_time", "end_time"],
	)
	current_datetime = frappe.flags.current_datetime or get_datetime()
	for shift in shifts:
		shift_end = get_actual_shift_end(shift, current_datetime)
		update_last_sync = None
		if shift.last_sync_of_checkin:
			if get_datetime(shift.last_sync_of_checkin) < shift_end < current_datetime:
				update_last_sync = True
		elif shift_end < current_datetime:
			update_last_sync = True
		if update_last_sync:
			frappe.db.set_value(
				"Shift Type", shift.name, "last_sync_of_checkin", shift_end + timedelta(minutes=1)
			)


def get_actual_shift_end(shift, current_datetime):
	time_within_shift = datetime.combine(current_datetime.date(), get_time(shift.start_time))
	shift_details = get_shift_details(shift.name, time_within_shift)
	actual_shift_start = shift_details["actual_start"]
	actual_shift_end = shift_details["actual_end"]

	if (actual_shift_start.date() < actual_shift_end.date()) or (current_datetime < actual_shift_start):
		# shift start and end are on different days
		actual_shift_end = add_days(actual_shift_end, -1)
	return actual_shift_end


def lock_employee_row(employee: str) -> None:
	"""Take the per-employee lock HR's master edit takes (S3 G6, W7).

	`SELECT … FOR UPDATE` on the Employee row, through the master edit's own
	seam so the three writers — hourly job, nightly recovery, HR's edit —
	queue behind each other for one person instead of both rebuilding the
	same day. Held until the caller commits: `_process` commits after each
	employee group, so a lock lives for one person's marking only. The
	nightly recovery calls this per employee.
	"""
	from hrms.api.attendance_master_edit import _employee

	_employee(employee, lock=True)
	logger.debug("[shift_type] employee row %s locked for marking", employee)


def process_auto_attendance_for_all_shifts():
	"""Called from hooks"""
	from hrms.utils.offshift_punch_heal import heal_recent_offshift_punches

	# A check-out saved without a shift is never read below; give recent ones
	# the shift of the check-in they close first (hrms/utils/offshift_punch_heal.py).
	# Nothing the heal does may stop attendance being marked this hour.
	try:
		heal_recent_offshift_punches()
	except Exception:
		logger.exception("[shift_type] off-shift punch heal failed; marking attendance anyway")
		try:
			frappe.log_error(title="Off-shift punch heal failed")
		except Exception:
			logger.exception("[shift_type] could not record the heal failure")
	shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
	for shift in shift_list:
		doc = frappe.get_cached_doc("Shift Type", shift)
		# One shift type failing (a lock wait behind the nightly recovery or
		# HR's master edit, E35) must not cost every other shift type its hour.
		try:
			doc.process_auto_attendance()
		except Exception:
			frappe.db.rollback()
			logger.exception("[shift_type] auto attendance failed for %s; other shifts continue", shift)
			try:
				frappe.log_error(title=f"Auto attendance failed for shift {shift}")
			except Exception:
				logger.exception("[shift_type] could not record the failure for %s", shift)
