"""Custom Employee Checkin override.

When an employee has multiple active Shift Assignments on the checkin date
(e.g. three shifts staggered by one hour), the stock HRMS logic prefers the
earliest. We instead pick the shift whose start_datetime is closest to the
actual checkin time. If the employee has at most one active assignment,
defer to the upstream `fetch_shift` implementation.
"""

from __future__ import annotations

import logging

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
	evaluate_geofence,
	resolve_assignment,
	resolve_location,
)

logger = logging.getLogger(__name__)


class CustomEmployeeCheckin(EmployeeCheckin):
	@frappe.whitelist()
	def fetch_shift(self):
		log_time = get_datetime(self.time)

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
			fields=["name", "shift_type", "start_date", "end_date"],
		)

		if len(active_assignments) <= 1:
			return super().fetch_shift()

		best = None
		best_delta = None
		for assignment in active_assignments:
			timings = (
				get_actual_start_end_datetime_of_shift(
					self.employee, log_time, True, for_shift=assignment["shift_type"]
				)
				if _supports_for_shift()
				else _resolve_timings_fallback(self.employee, log_time, assignment)
			)

			if not timings or not timings.get("start_datetime"):
				continue

			shift_start = get_datetime(timings["start_datetime"])
			delta = abs((shift_start - log_time).total_seconds())
			if best_delta is None or delta < best_delta:
				best = timings
				best_delta = delta

		if not best:
			logger.info(
				"[employee_checkin] No resolvable shift among %d assignments for %s @ %s",
				len(active_assignments),
				self.employee,
				log_time,
			)
			self.shift = None
			self.offshift = 1
			return

		shift_type = best.get("shift_type")
		shift_type_name = shift_type.name if hasattr(shift_type, "name") else shift_type
		if not self.attendance:
			self.offshift = 0
			self.shift = shift_type_name
			self.shift_actual_start = best.get("actual_start")
			self.shift_actual_end = best.get("actual_end")
			self.shift_start = best.get("start_datetime")
			self.shift_end = best.get("end_datetime")

		logger.info(
			"[employee_checkin] Picked closest shift=%s for %s @ %s (delta=%.0fs)",
			shift_type_name,
			self.employee,
			log_time,
			best_delta or 0,
		)

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
		if getattr(self.flags, "is_late_checkout", False):
			logger.info(
				"[employee_checkin] Skipping geofence validation for late checkout %s",
				self.name or "(new)",
			)
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
			return

		if not (self.latitude and self.longitude):
			# Thrown here rather than delegated to `super()`. Upstream re-reads the
			# GLOBAL flag, so delegating reopened the same bypass one level down;
			# it also guards on `or`, which let a half-supplied coordinate pair
			# through to a distance calculation against None.
			logger.info(
				"[employee_checkin] geofence refused employee=%s — no usable lat/long on doc",
				self.employee,
			)
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		if not self.shift:
			# fetch_shift() couldn't resolve a Shift Type (no assignment, or
			# multi-assignment edge case where every option failed). We can't
			# look up a Shift Location without a shift_type, so we silently
			# allow — but log it so FC operators can diagnose missing dialogs.
			logger.info(
				"[employee_checkin] geofence silent-allow employee=%s — no shift resolved (self.shift is None)",
				self.employee,
			)
			return

		# One resolver, shared with the preflight. It deliberately does NOT filter
		# on `shift_location is set`: `enable_strict_geofence` is read off the row
		# the filter selects, so a strict assignment with no location used to match
		# nothing and silently degrade to lenient — the one combination that most
		# needs to throw.
		assignment = resolve_assignment(self.employee, self.time, shift_type=self.shift)
		shift_loc_name = assignment.shift_location if assignment else None
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

		decision = evaluate_geofence(
			strict=strict,
			has_shift_location=bool(shift_loc_name and row),
			radius_m=radius_m,
			distance_m=distance,
			accuracy_m=accuracy_m,
		)
		if decision is None:
			# Lenient silent-allow paths land here. Spell out which one fired
			# so the FC logs can pin down "why didn't the remote dialog appear?".
			if not shift_loc_name:
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — no shift_location on active Shift Assignment",
					self.employee,
					self.shift,
					strict,
				)
			elif not row:
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — Shift Location %s row missing",
					self.employee,
					self.shift,
					strict,
					shift_loc_name,
				)
			elif radius_m <= 0:
				logger.info(
					"[employee_checkin] geofence silent-allow employee=%s shift=%s strict=%s — Shift Location %s has no check-in radius",
					self.employee,
					self.shift,
					strict,
					shift_loc_name,
				)
			else:
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
		if action == "throw":
			self._throw_strict_geofence(ctx, shift_loc_name)
			return

		# action == "require_remote" — lenient mode, out of radius
		self.requires_remote_approval = 1
		self.remote_approval_status = "Pending"
		# Stash for after_insert hook (these are doc attrs, not DB columns).
		self._remote_distance_m = ctx["overshoot_m"]
		self._remote_nearest_location = shift_loc_name
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
			"[employee_checkin] Strict geofence reject employee=%s shift=%s reason=%s",
			self.employee,
			self.shift,
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
	try:
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
		# The strict throw that follows this call rolls back the request
		# transaction — the very one that just wrote this row — so without an
		# explicit commit the audit trace is discarded with it. Bench-verified:
		# the row existed before the rollback and was gone after, which is why
		# production carried zero Geofence Reject Logs despite every rejection
		# writing one. Commit it now. Safe: validate_distance_from_shift_location
		# runs pre-insert, so no Employee Checkin row is pending — this cannot
		# persist a check-in for the rejected attempt — and the punch/Desk write
		# paths have no other uncommitted change to carry along. Skipped under the
		# test runner, which depends on one rolled-back transaction for isolation.
		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep: durable audit must survive the strict throw
		logger.info(
			"[employee_checkin] Wrote Geofence Reject Log %s employee=%s reason=%s (committed)",
			log.name,
			doc.employee,
			ctx.get("reason"),
		)
	except Exception as exc:
		logger.warning(
			"[employee_checkin] Failed to write Geofence Reject Log employee=%s reason=%s: %s",
			doc.employee,
			ctx.get("reason"),
			exc,
		)


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
	}
