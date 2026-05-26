"""Pre-flight geofence checks for the SPA check-in flow.

Public API:
    check_geofence(employee, log_type, latitude, longitude, time=None)
        Returns a JSON-serialisable dict the frontend uses to decide
        whether to open the normal check-in modal, the lenient
        Remote Checkin Request dialog (handled post-insert today), or
        the new Strict Rejection dialog (must abort before insert).

This endpoint is read-only — it never inserts a check-in row.

Response shape:
    {"ok": True, "mode": "ok"}
        Proceed with insert.

    {"ok": False, "mode": "strict_block",
     "reason": "outside_radius" | "no_shift_location" | "no_radius",
     "shift_type": str | None,
     "shift_location": str | None,
     "shift_location_name": str | None,
     "distance_m": float | None,
     "radius_m": int | None,
     "overshoot_m": float | None}
        SPA should display StrictRejectionDialog with these details and
        abort the insert. A real insert attempt would throw
        CheckinRadiusExceededError.
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import get_datetime, now_datetime

from hrms.hr.utils import get_distance_between_coordinates
from hrms.utils.geofence import evaluate_geofence

logger = logging.getLogger(__name__)


def _ok() -> dict:
	return {"ok": True, "mode": "ok"}


def _strict_block(reason, shift_type, shift_loc_name, ctx) -> dict:
	return {
		"ok": False,
		"mode": "strict_block",
		"reason": reason,
		"shift_type": shift_type,
		"shift_location": shift_loc_name,
		"distance_m": ctx.get("distance_m"),
		"radius_m": ctx.get("radius_m"),
		"overshoot_m": ctx.get("overshoot_m"),
	}


@frappe.whitelist()
def check_geofence(employee, log_type, latitude=None, longitude=None, time=None):
	"""Preflight a check-in: would inserting it right now succeed under
	the Shift Type's geofence policy?

	Args:
		employee: Employee.name
		log_type: "IN" or "OUT"
		latitude, longitude: caller's current GPS reading
		time: optional ISO datetime; defaults to now. Used to resolve which
		      shift assignment is active.
	"""
	logger.info(
		"[geofence.api] preflight employee=%s log_type=%s lat=%s lng=%s time=%s",
		employee,
		log_type,
		latitude,
		longitude,
		time,
	)

	if not employee:
		return _ok()

	if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
		return _ok()

	try:
		lat = float(latitude) if latitude not in (None, "") else None
		lng = float(longitude) if longitude not in (None, "") else None
	except (TypeError, ValueError):
		lat = lng = None

	if lat is None or lng is None:
		# Without coordinates the server can't preflight; let the insert path
		# enforce its own "coordinates required" throw.
		return _ok()

	at = get_datetime(time) if time else now_datetime()

	# Resolve the strict flag via active Shift Assignment + Shift Type.
	assignment = frappe.db.sql(
		"""
		SELECT sa.name, sa.shift_type, sa.shift_location, st.enable_strict_geofence
		FROM `tabShift Assignment` sa
		JOIN `tabShift Type` st ON st.name = sa.shift_type
		WHERE sa.employee = %s
		  AND sa.docstatus = 1
		  AND sa.status = 'Active'
		  AND sa.start_date <= %s
		  AND (sa.end_date IS NULL OR sa.end_date >= %s)
		ORDER BY sa.start_date DESC
		LIMIT 1
		""",
		(employee, at.date(), at.date()),
		as_dict=True,
	)
	if not assignment:
		logger.info("[geofence.api] no active shift assignment for %s — pass-through", employee)
		return _ok()

	row = assignment[0]
	strict = bool(row.enable_strict_geofence)
	if not strict:
		# Lenient mode is handled post-insert by the existing
		# RemoteCheckinDialog flow — no preflight needed.
		return _ok()

	shift_loc_name = row.shift_location

	loc = None
	if shift_loc_name:
		loc = frappe.db.get_value(
			"Shift Location",
			shift_loc_name,
			["checkin_radius", "latitude", "longitude"],
			as_dict=True,
		)

	radius_m = int(loc.checkin_radius) if loc and loc.checkin_radius else 0
	distance_m = None
	if loc and loc.latitude is not None and loc.longitude is not None:
		distance_m = get_distance_between_coordinates(loc.latitude, loc.longitude, lat, lng)

	decision = evaluate_geofence(
		strict=True,
		has_shift_location=bool(shift_loc_name and loc),
		radius_m=radius_m,
		distance_m=distance_m,
	)
	if decision is None:
		return _ok()

	action, ctx = decision
	if action == "throw":
		logger.info(
			"[geofence.api] strict block employee=%s reason=%s distance=%s",
			employee,
			ctx.get("reason"),
			ctx.get("distance_m"),
		)
		return _strict_block(ctx.get("reason"), row.shift_type, shift_loc_name, ctx)

	# Strict path should not return require_remote (helper only emits it for
	# lenient mode). Defensive — treat anything unexpected as pass-through.
	logger.warning("[geofence.api] unexpected decision under strict mode: %s", decision)
	return _ok()
