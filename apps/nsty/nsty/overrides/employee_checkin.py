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
from frappe.utils import get_datetime

from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)
from hrms.hr.utils import get_distance_between_coordinates

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
		"""Replace HRMS strict geofence rejection with the remote-checkin flow.

		Behaviour:
		  - flags.is_late_checkout set -> skip entirely (retroactive submission,
		    no current location to validate against).
		  - Geolocation tracking disabled -> nothing to do.
		  - No active Shift Assignment with shift_location -> nothing to do
		    (employee not tied to any geofence).
		  - Inside the configured radius -> accept silently.
		  - Outside the radius -> ALLOW the save and flag the doc so the
		    after_insert hook auto-creates a Remote Checkin Request awaiting
		    manager approval.
		"""
		if getattr(self.flags, "is_late_checkout", False):
			logger.info(
				"[employee_checkin] Skipping geofence validation for late checkout %s",
				self.name or "(new)",
			)
			return

		if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
			return

		if not (self.latitude and self.longitude):
			# No coordinates captured — fall through to upstream behaviour which
			# throws. The frontend always sends lat/long when geo is enabled.
			return super().validate_distance_from_shift_location()

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

		shift_loc_name = assignment_locations[0]
		row = frappe.db.get_value(
			"Shift Location",
			shift_loc_name,
			["checkin_radius", "latitude", "longitude"],
			as_dict=True,
		)
		if not row or not row.checkin_radius or row.checkin_radius <= 0:
			return

		distance = get_distance_between_coordinates(
			row.latitude, row.longitude, self.latitude, self.longitude
		)
		if distance <= row.checkin_radius:
			# Inside the geofence — happy path.
			return

		# Outside the geofence — allow but flag for approval.
		self.requires_remote_approval = 1
		self.remote_approval_status = "Pending"
		# Stash for after_insert hook (these are doc attrs, not DB columns).
		self._remote_distance_m = max(0.0, distance - (row.checkin_radius or 0))
		self._remote_nearest_location = shift_loc_name
		logger.info(
			"[employee_checkin] Remote check-in flagged employee=%s log_type=%s distance=%.1fm radius=%sm location=%s",
			self.employee,
			self.log_type,
			distance,
			row.checkin_radius,
			shift_loc_name,
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
