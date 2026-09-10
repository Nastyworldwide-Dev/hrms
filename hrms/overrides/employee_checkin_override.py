"""Custom Employee Checkin override.

When an employee has multiple active Shift Assignments on the checkin date
(e.g. three shifts staggered by one hour), the stock HRMS logic prefers the
earliest. We instead pick the shift whose start_datetime is closest to the
actual checkin time. If the employee has at most one active assignment,
defer to the upstream `fetch_shift` implementation.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime

from hrms.hr.doctype.employee_checkin.employee_checkin import (
	CheckinRadiusExceededError,
	EmployeeCheckin,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)
from hrms.hr.utils import get_distance_between_coordinates
from hrms.utils.company_settings import is_setting_enabled_for_employee
from hrms.utils.geofence import (
	REASON_IMPRECISE_LOCATION,
	REASON_NO_RADIUS,
	REASON_NO_SHIFT_LOCATION,
	REASON_OUTSIDE_RADIUS,
	effective_shift_location,
	evaluate_geofence,
	parse_coordinates,
	resolve_assignment,
	resolve_location,
)

logger = logging.getLogger(__name__)


class CustomEmployeeCheckin(EmployeeCheckin):
	@frappe.whitelist()
	def fetch_shift(self):
		log_time = get_datetime(self.time)

		# A check-out closes the shift its own check-in opened, whatever the
		# clock says. Before this, the shift's check-out grace window decided
		# alone, so a 9-6 employee who worked until 00:32 had that punch filed
		# off-shift, the day computed from the check-in alone, and fifteen hours
		# recorded as none (probed 10 Sep 2026). Worse, a check-out the next
		# morning landed inside the NEXT day's window and broke two days at once.
		# Anchored to a real open IN, so it cannot adopt a stray punch.
		if self._close_open_session():
			return

		active_assignments = frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"status": "Active",
				"docstatus": 1,
				"start_date": ["<=", log_time.date()],
			},
			or_filters=[
				["end_date", ">=", log_time.date()],
				["end_date", "is", "not set"],
			],
			fields=["name", "shift_type", "start_date", "end_date", "overtime_type"],
		)

		if len(active_assignments) <= 1:
			super().fetch_shift()
			# Arriving before the shift's own early grace left the punch
			# off-shift, so the day was computed from the check-out alone and
			# came out at zero hours — the same loss as a late check-out, at the
			# other end. An early arrival is presence: it belongs to the shift it
			# precedes. The hours still start at the shift
			# (ShiftType.unpaid_hours_before_shift), so nothing is paid for it.
			if not self.shift and self.log_type == "IN" and active_assignments:
				self._attach_early_arrival(active_assignments[0], log_time)
			return

		from hrms.utils.shift_resolution import choose_shift

		# Windows anchored on the punch date AND the day before: a night shift's
		# OUT at 03:30 belongs to the shift that started yesterday.
		candidates = []
		for assignment in active_assignments:
			for anchor in (log_time, log_time - timedelta(days=1)):
				timings = _resolve_timings_fallback(self.employee, anchor, assignment)
				if timings and timings.get("actual_start") and timings.get("actual_end"):
					candidates.append(timings)
		best = choose_shift(log_time, self.log_type, candidates, self._open_in())

		if not best:
			logger.info(
				"[employee_checkin] %s @ %s falls in none of %d assigned shift windows for %s: off-shift",
				self.log_type,
				log_time,
				len(active_assignments),
				self.employee,
			)
			self.shift = None
			self.offshift = 1
			return

		shift_type = best.get("shift_type")
		shift_type_name = shift_type.name if hasattr(shift_type, "name") else shift_type
		self._stamp_shift(
			shift=shift_type_name,
			start_datetime=best.get("start_datetime"),
			end_datetime=best.get("end_datetime"),
			actual_start=best.get("actual_start"),
			actual_end=best.get("actual_end"),
			overtime_type=best.get("overtime_type"),
		)

		logger.info(
			"[employee_checkin] shift=%s for %s %s @ %s (%d assignments)",
			shift_type_name,
			self.employee,
			self.log_type,
			log_time,
			len(active_assignments),
		)

	def _stamp_shift(
		self, *, shift, start_datetime, end_datetime, actual_start, actual_end, overtime_type
	) -> None:
		"""Give this punch a shift — the whole stamp, never a part of it.

		overtime_type is the part that was missed three times over, and its loss
		is silent: the hourly job takes the day's overtime type from the FIRST
		eligible punch (ShiftType.get_attendance), so one punch stamped None
		makes the whole day ineligible and the overtime never reaches the slip.

		A punch already linked to an Attendance row is never re-derived —
		bulk_fetch_shift re-runs fetch_shift over linked punches, and upstream
		relies on the same guard.
		"""
		if self.attendance:
			return
		self.offshift = 0
		self.shift = shift
		self.shift_start = start_datetime
		self.shift_end = end_datetime
		self.shift_actual_start = actual_start
		self.shift_actual_end = actual_end
		self.overtime_type = overtime_type or None
		logger.info(
			"[employee_checkin] %s %s @ %s stamped shift=%s overtime_type=%s",
			self.employee,
			self.log_type,
			self.time,
			shift,
			self.overtime_type,
		)

	def _attach_early_arrival(self, assignment, log_time) -> None:
		"""An IN that lands before the day's shift window belongs to that shift.

		Only earlier, never later: a punch AFTER the window closed is not an
		early arrival, and leaving it off-shift is right. Bounded to the shift's
		own day, so this can never reach into another day's shift.
		"""
		timings = _resolve_timings_fallback(self.employee, log_time, assignment)
		if not timings or not timings.get("actual_start"):
			return
		if log_time >= get_datetime(timings["actual_start"]):
			return
		if get_datetime(timings["start_datetime"]).date() != log_time.date():
			return
		self._stamp_shift(
			shift=assignment["shift_type"],
			start_datetime=timings.get("start_datetime"),
			end_datetime=timings.get("end_datetime"),
			actual_start=timings.get("actual_start"),
			actual_end=timings.get("actual_end"),
			overtime_type=assignment.get("overtime_type") or timings.get("overtime_type"),
		)
		logger.info(
			"[employee_checkin] %s arrived at %s, before %s opens at %s — counted from the shift start",
			self.employee,
			log_time,
			self.shift,
			timings.get("start_datetime"),
		)

	def _close_open_session(self) -> bool:
		"""An OUT inherits the whole shift stamp of the IN it closes. True when
		it did, so the caller stops. Never fires for an IN, for a punch already
		attached to attendance, or when the open IN carries no shift."""
		if self.log_type != "OUT" or self.attendance:
			return False
		# A late check-out is a forgotten one, so the gap is unbounded by
		# definition, and fetch_shift would otherwise overwrite its shift with
		# whatever window the clock falls in — filing yesterday's missing
		# check-out against today and breaking both days. The caller names the
		# IN it is closing; re-deriving it would let the search adopt a stale
		# unclosed IN from an earlier day, whatever the gap.
		named = getattr(self.flags, "late_checkout_in", None)
		if named:
			open_in = {"name": named, "shift": frappe.db.get_value("Employee Checkin", named, "shift")}
		else:
			open_in = self._open_in(bounded=not getattr(self.flags, "is_late_checkout", False))
		if not open_in or not open_in.get("shift"):
			return False
		row = frappe.db.get_value(
			"Employee Checkin",
			open_in["name"],
			[
				"shift",
				"shift_start",
				"shift_end",
				"shift_actual_start",
				"shift_actual_end",
				"overtime_type",
			],
			as_dict=True,
		)
		if not row or not row.shift:
			return False
		self._stamp_shift(
			shift=row.shift,
			start_datetime=row.shift_start,
			end_datetime=row.shift_end,
			actual_start=row.shift_actual_start,
			actual_end=row.shift_actual_end,
			overtime_type=row.overtime_type,
		)
		logger.info(
			"[employee_checkin] OUT %s closes the session opened by %s on %s",
			self.time,
			open_in["name"],
			row.shift,
		)
		return True

	def _open_in(self, bounded: bool = True) -> dict | None:
		"""The employee's latest IN with no OUT after it — the session an OUT
		closes. Its shift is the OUT's shift, whatever window the clock says.

		`bounded` keeps an ordinary check-out inside the session window, so it
		can never adopt a punch from days ago. A late check-out, which the
		employee submits precisely because the gap is long, searches back
		without that bound.
		"""
		from hrms.utils.shift_resolution import SESSION_WINDOW

		log_time = get_datetime(self.time)
		# ceiling: an unnamed late check-out searches back 14 days; upgrade: every
		# caller should set flags.late_checkout_in, and then this bound can go.
		earliest = log_time - SESSION_WINDOW if bounded else log_time - timedelta(days=14)
		rows = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": self.employee,
				"time": ("between", [earliest, log_time]),
				"name": ("!=", self.name),
			},
			fields=["name", "shift", "time", "log_type"],
			order_by="time desc",
			limit_page_length=1,
		)
		if not rows or rows[0].log_type != "IN":
			return None
		return {"name": rows[0].name, "shift": rows[0].shift, "time": get_datetime(rows[0].time)}

	def _is_manual_entry(self) -> bool:
		"""A punch a person keys in for SOMEONE ELSE. The employee's own punch
		always carries coordinates from the PWA; a bare one from them is refused."""
		user = frappe.session.user
		if not user or user == "Guest" or self.device_id or getattr(self.flags, "integration_entry", False):
			return False
		return user != frappe.db.get_value("Employee", self.employee, "user_id")

	def validate_distance_from_shift_location(self):
		"""Geofence validation with two modes.

		Mode is driven by Shift Assignment.enable_strict_geofence:
		  - Lenient (default): out-of-radius check-ins are allowed and flagged
		    for the after_insert hook to spawn a Remote Checkin Request.
		  - Strict: out-of-radius check-ins are rejected outright with
		    CheckinRadiusExceededError. Missing shift location or zero radius
		    on the assignment also throw under strict mode.

		Late check-outs (flags.is_late_checkout) bypass geofencing entirely
		in both modes — they are retroactive submissions and have no current
		location to validate against.
		"""
		# Evidence first: what the device said travels onto the row whatever the
		# fence decides, so HR can later ask "why did this read as outside?" and
		# find the accuracy, the fix age and the provider next to the answer.
		self.location_accuracy_m = getattr(self.flags, "location_accuracy_m", None)
		self.location_fix_age_s = getattr(self.flags, "location_fix_age_s", None)
		self.location_source = getattr(self.flags, "location_source", None)
		self.geofence_distance_m = None
		self.geofence_radius_m = None

		if getattr(self.flags, "is_late_checkout", False):
			logger.info(
				"[employee_checkin] Skipping geofence validation for late checkout %s",
				self.name or "(new)",
			)
			self.geofence_outcome = "Late Checkout"
			return

		# Per COMPANY, not the global singleton. Geolocated check-in is a
		# per-entity rollout decision, and reading the global here meant a company
		# that had switched it ON was warned by the preflight
		# (`hrms.api.geofence.check_geofence`, which always asked per company) and
		# never blocked at the insert — the flag did nothing where it counted.
		if not is_setting_enabled_for_employee(self.employee, "allow_geolocation_tracking"):
			logger.info(
				"[employee_checkin] geofence skipped employee=%s — geolocation tracking off for their company",
				self.employee,
			)
			self.geofence_outcome = "Tracking Off"
			return

		coordinates = parse_coordinates(self.latitude, self.longitude)
		if coordinates is None and self._is_manual_entry():
			# HR keying a check-in for someone else in Desk (the employee came in,
			# the phone did not record it). There is nothing to fence and no
			# approver to ask: it is recorded as HR's word, named as such.
			self.geofence_outcome = "Manual Entry"
			logger.info(
				"[employee_checkin] manual entry for %s by %s — no coordinates, no fence",
				self.employee,
				frappe.session.user,
			)
			return
		if coordinates is None:
			# Thrown here rather than delegated to `super()`. Upstream re-reads the
			# GLOBAL flag, so delegating reopened the same bypass one level down;
			# it also guards on `or`, which let a half-supplied coordinate pair
			# through to a distance calculation against None.
			logger.info("[employee_checkin] geofence refused invalid coordinate pair")
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		self.latitude, self.longitude = coordinates

		if not self.shift:
			# fetch_shift() couldn't resolve a Shift Type (no assignment, or
			# multi-assignment edge case where every option failed). We can't
			# look up a Shift Location without a shift_type, so we silently
			# allow — but log it so FC operators can diagnose missing dialogs.
			logger.info(
				"[employee_checkin] geofence silent-allow employee=%s — no shift resolved (self.shift is None)",
				self.employee,
			)
			# Still an allow — HR's call whether it should be — but no longer
			# invisible: the row says nothing was checked, and the report counts it.
			self.geofence_outcome = "No Shift"
			return

		# One resolver, shared with the preflight. It deliberately does NOT filter
		# on `shift_location is set`: `enable_strict_geofence` is read off the row
		# the filter selects, so a strict assignment with no location used to match
		# nothing and silently degrade to lenient — the one combination that most
		# needs to throw.
		assignment = resolve_assignment(self.employee, self.time, shift_type=self.shift)
		# Assignment's shift_location, or the Employee's own when the assignment
		# carries none (manual/schedule) — the same fallback the preflight uses,
		# so the screen that warns and the code that enforces stay in step.
		shift_loc_name = effective_shift_location(self.employee, assignment)
		# Strict flag lives on Shift Assignment (was on Shift Type up to v15.77.3).
		# No active assignment at all still means lenient, so untagged check-ins
		# keep falling through to the silent-allow / remote-approval paths.
		strict = bool(assignment.enable_strict_geofence) if assignment else False

		row = resolve_location(shift_loc_name)

		radius_m = int(row.checkin_radius) if row and row.checkin_radius else 0
		distance = None
		if row and row.latitude is not None and row.longitude is not None:
			distance = get_distance_between_coordinates(
				row.latitude, row.longitude, self.latitude, self.longitude
			)

		# How sure the device was about the coordinates it sent. Carried as a
		# flag rather than a column: it is an input to this decision, not a
		# property of the punch, and a Desk or biometric row has no browser
		# behind it to supply one. Absent means unknown, which buys nothing.
		accuracy_m = getattr(self.flags, "location_accuracy_m", None)
		self.geofence_distance_m = round(distance, 1) if distance is not None else None
		self.geofence_radius_m = radius_m or None

		free_location = bool(row and getattr(row, "is_free_location", 0))
		decision = evaluate_geofence(
			strict=strict,
			has_shift_location=bool(shift_loc_name and row),
			radius_m=radius_m,
			distance_m=distance,
			accuracy_m=accuracy_m,
			free_location=free_location,
		)
		if decision is None:
			# Lenient silent-allow paths land here. Spell out which one fired
			# so the FC logs can pin down "why didn't the remote dialog appear?".
			if free_location:
				self.geofence_outcome = "Free Location"
				logger.info(
					"[employee_checkin] free location employee=%s shift=%s location=%s — recorded, no approval",
					self.employee,
					self.shift,
					shift_loc_name,
				)
			elif not shift_loc_name:
				self.geofence_outcome = "No Location"
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — no shift_location on active Shift Assignment",
					self.employee,
					self.shift,
					strict,
				)
			elif not row:
				self.geofence_outcome = "No Location"
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — Shift Location %s row missing",
					self.employee,
					self.shift,
					strict,
					shift_loc_name,
				)
			elif radius_m <= 0:
				self.geofence_outcome = "No Radius"
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — Shift Location %s has no check-in radius",
					self.employee,
					self.shift,
					strict,
					shift_loc_name,
				)
			else:
				self.geofence_outcome = "Inside"
				logger.info(
					"[employee_checkin] geofence inside radius employee=%s shift=%s distance=%.1fm radius=%dm accuracy=%sm location=%s",
					self.employee,
					self.shift,
					distance or 0.0,
					radius_m,
					accuracy_m,
					shift_loc_name,
				)
			return

		action, ctx = decision
		self.geofence_outcome = "Imprecise" if ctx.get("reason") == REASON_IMPRECISE_LOCATION else "Outside"
		if action == "throw":
			self._throw_strict_geofence(ctx, shift_loc_name)
			return

		# action == "require_remote" — lenient mode, out of radius
		self.requires_remote_approval = 1
		self.remote_approval_status = "Pending"
		# Stash for after_insert hook (these are doc attrs, not DB columns).
		self._remote_distance_m = ctx["overshoot_m"]
		self._remote_nearest_location = shift_loc_name
		self._remote_radius_m = ctx.get("radius_m")
		# Why this punch needs approving. Returned to the PWA by the punch
		# endpoint so the dialog can say "we could not place you" instead of
		# "you are 0 m outside the geofence", which is what an unplaceable
		# reading computes to and is not something anyone should be shown.
		self._remote_reason = ctx["reason"]
		logger.info(
			"[employee_checkin] Remote check-in flagged employee=%s log_type=%s reason=%s distance=%.1fm radius=%dm accuracy=%.0fm location=%s",
			self.employee,
			self.log_type,
			ctx["reason"],
			ctx["distance_m"],
			ctx["radius_m"],
			ctx.get("accuracy_m") or 0.0,
			shift_loc_name,
		)

	def _throw_strict_geofence(self, ctx, shift_loc_name):
		reason = ctx.get("reason")
		logger.info(
			"[employee_checkin] Strict geofence reject reason=%s",
			reason,
		)
		_record_geofence_reject(self, ctx, shift_loc_name)
		if reason == REASON_NO_SHIFT_LOCATION:
			frappe.throw(
				frappe._(
					"Strict geofencing is enabled for shift {0}, but no Shift Location "
					"is configured on your Shift Assignment. Contact your HR administrator."
				).format(self.shift or ""),
				exc=CheckinRadiusExceededError,
			)
		if reason == REASON_NO_RADIUS:
			frappe.throw(
				frappe._(
					"Strict geofencing is enabled for shift {0}, but Shift Location {1} "
					"has no check-in radius configured. Contact your HR administrator."
				).format(self.shift or "", shift_loc_name or ""),
				exc=CheckinRadiusExceededError,
			)
		if reason == REASON_IMPRECISE_LOCATION:
			# Deliberately not phrased as "you are N m away" — the whole point
			# is that we do not know where they are, and quoting a distance
			# from an unusable fix reads as an accusation the data can't make.
			frappe.throw(
				frappe._(
					"Your device could only place you to within {0} m, which is too "
					"imprecise to check you in against the {1} geofence. Move somewhere "
					"with a clearer view of the sky or a known wifi network and try again."
				).format(int(ctx.get("accuracy_m") or 0), shift_loc_name or ""),
				exc=CheckinRadiusExceededError,
			)
		# REASON_OUTSIDE_RADIUS
		frappe.throw(
			frappe._(
				"You are {0:.0f} m outside the {1} check-in radius ({2} m). "
				"Move closer to check in. Remote approval is not available for this shift."
			).format(ctx.get("distance_m") or 0.0, shift_loc_name or "", ctx.get("radius_m") or 0),
			exc=CheckinRadiusExceededError,
		)


def _record_geofence_reject(doc, ctx, shift_loc_name):
	"""Persist a Geofence Reject Log row before the strict throw.

	Failure to write must not block the user-facing throw — the log is for
	auditing, not flow control. Any error here is downgraded to a warning.
	"""
	# The caller may already hold unrelated writes. A refused punch must never
	# commit them, including when invoked by a worker or the test runner.
	from frappe.database import get_db

	caller = frappe.local.db
	missing = object()
	context = {key: getattr(frappe.local, key, missing) for key in ("flags", "_realtime_log", "message_log")}
	try:
		audit_db = get_db(
			socket=caller.socket,
			host=caller.host,
			port=caller.port,
			user=caller.user,
			password=caller.password,
			cur_db_name=caller.cur_db_name,
		)
		try:
			frappe.local.db = audit_db
			frappe.local.flags = frappe._dict(frappe.local.flags)
			frappe.local.flags.currently_saving = list(frappe.local.flags.currently_saving or [])
			frappe.local.message_log = []
			if hasattr(frappe.local, "_realtime_log"):
				del frappe.local._realtime_log
			log = frappe.new_doc("Geofence Reject Log")
			log.update(
				{
					"employee": doc.employee,
					"log_type": doc.log_type or "IN",
					"rejected_at": doc.time or frappe.utils.now_datetime(),
					"shift_type": doc.shift,
					"shift_location": shift_loc_name,
					"reason": ctx.get("reason"),
					"distance_m": ctx.get("distance_m"),
					"radius_m": ctx.get("radius_m"),
					"overshoot_m": ctx.get("overshoot_m"),
					"accuracy_m": ctx.get("accuracy_m"),
					"latitude": doc.latitude,
					"longitude": doc.longitude,
					"device_id": getattr(doc, "device_id", None),
				}
			)
			log.flags.ignore_permissions = True
			log.insert()
			audit_db.commit()
			logger.info("[employee_checkin] Isolated geofence refusal audit persisted")
		except Exception:
			audit_db.rollback()
			raise
		finally:
			frappe.local.db = caller
			for key, value in context.items():
				if value is missing:
					if hasattr(frappe.local, key):
						delattr(frappe.local, key)
				else:
					setattr(frappe.local, key, value)
			audit_db.close()
	except Exception as exc:
		logger.warning("[employee_checkin] Isolated geofence refusal audit failed (%s)", type(exc).__name__)


def _supports_for_shift() -> bool:
	import inspect

	try:
		sig = inspect.signature(get_actual_start_end_datetime_of_shift)
		return "for_shift" in sig.parameters
	except (TypeError, ValueError):
		return False


def _resolve_timings_fallback(employee, log_time, assignment):
	"""Compute shift timings for a specific assignment when upstream doesn't
	support a `for_shift` kwarg. Builds start/end from Shift Type start_time
	& end_time anchored on the checkin date.
	"""
	from datetime import datetime, timedelta

	shift_type_doc = frappe.get_cached_doc("Shift Type", assignment["shift_type"])
	base_date = log_time.date()
	start_dt = (
		datetime.combine(base_date, datetime.strptime(str(shift_type_doc.start_time), "%H:%M:%S").time())
		if ":" in str(shift_type_doc.start_time)
		else None
	)
	end_dt = (
		datetime.combine(base_date, datetime.strptime(str(shift_type_doc.end_time), "%H:%M:%S").time())
		if ":" in str(shift_type_doc.end_time)
		else None
	)
	if not start_dt or not end_dt:
		return None
	if end_dt <= start_dt:
		end_dt += timedelta(days=1)

	before_grace = timedelta(minutes=shift_type_doc.get("begin_check_in_before_shift_start_time") or 60)
	after_grace = timedelta(minutes=shift_type_doc.get("allow_check_out_after_shift_end_time") or 60)

	return {
		"shift_type": shift_type_doc,
		"start_datetime": start_dt,
		"end_datetime": end_dt,
		"actual_start": start_dt - before_grace,
		"actual_end": end_dt + after_grace,
		# The assignment overrides the Shift Type, exactly as upstream's
		# get_actual_start_end_datetime_of_shift resolves it.
		"overtime_type": assignment.get("overtime_type") or shift_type_doc.get("overtime_type") or None,
	}
