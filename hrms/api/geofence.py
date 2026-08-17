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
from frappe.utils import get_datetime

from hrms.api import _ensure_own_employee_or_permitted
from hrms.hr.utils import get_distance_between_coordinates
from hrms.utils.company_settings import is_company_setting_enabled
from hrms.utils.geofence import evaluate_geofence
from hrms.utils.timezone import employee_now

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
	# Everything below reads through raw SQL and `db.get_value`, both of which
	# bypass the document permission layer — so before this line, nothing in the
	# call refused anybody. Measured rather than assumed: acting as a plain
	# Employee-role user, this answered `{"ok": True, "mode": "ok"}` for a
	# COLLEAGUE, which is a live answer to "is that person at their work site
	# right now". Every other open read here leaked a fact about somebody; this
	# one tracked them.
	#
	# Not self-only — the helper also passes anyone with real read permission on
	# the Employee doc, so HR and approvers keep working. The PWA only ever asks
	# about the signed-in user.
	_ensure_own_employee_or_permitted(employee)

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

	# Geolocated check-in is rolled out per company. A company with no override
	# inherits the global HR Settings flag — i.e. today's behaviour exactly.
	company = frappe.db.get_value("Employee", employee, "company")
	if not is_company_setting_enabled(company, "allow_geolocation_tracking"):
		logger.info("[geofence.api] geolocation tracking off for company=%s — pass-through", company)
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

	# Resolve the shift as of the employee's own wall clock — a site clock in
	# a different timezone matches the wrong shift near boundary hours.
	at = get_datetime(time) if time else employee_now(employee)

	# Strict flag now lives on Shift Assignment (moved from Shift Type in v15.77.4).
	assignment = frappe.db.sql(
		"""
		SELECT sa.name, sa.shift_type, sa.shift_location, sa.enable_strict_geofence
		FROM `tabShift Assignment` sa
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


@frappe.whitelist()
def get_active_shift_location(employee: str, time: str | None = None) -> dict | None:
	"""Return the Shift Location attached to the employee's active assignment,
	along with the strict flag, for the SPA's check-in map.

	Lightweight read used by the check-in modal to draw the location pin +
	radius circle before the user submits. Returns None when no active
	assignment matches or the assignment has no shift_location.
	"""
	if not employee:
		return None

	# Same fence, same reason as check_geofence: the SQL below answers with a
	# colleague's work coordinates — location_name, latitude, longitude, radius —
	# and nothing in the query has any notion of who is asking.
	_ensure_own_employee_or_permitted(employee)

	# Resolve the shift as of the employee's own wall clock — a site clock in
	# a different timezone matches the wrong shift near boundary hours.
	at = get_datetime(time) if time else employee_now(employee)
	logger.debug("[geofence.api] get_active_shift_location employee=%s at=%s", employee, at)

	row = frappe.db.sql(
		"""
		SELECT sa.shift_location, sa.enable_strict_geofence, sa.shift_type
		FROM `tabShift Assignment` sa
		WHERE sa.employee = %s
		  AND sa.docstatus = 1
		  AND sa.status = 'Active'
		  AND sa.start_date <= %s
		  AND (sa.end_date IS NULL OR sa.end_date >= %s)
		  AND sa.shift_location IS NOT NULL
		ORDER BY sa.start_date DESC
		LIMIT 1
		""",
		(employee, at.date(), at.date()),
		as_dict=True,
	)
	if not row:
		return None

	r = row[0]
	loc = frappe.db.get_value(
		"Shift Location",
		r.shift_location,
		["name", "location_name", "latitude", "longitude", "checkin_radius"],
		as_dict=True,
	)
	if not loc or loc.latitude is None or loc.longitude is None:
		return None

	return {
		"shift_location": loc.name,
		"label": loc.location_name or loc.name,
		"latitude": float(loc.latitude),
		"longitude": float(loc.longitude),
		"checkin_radius": int(loc.checkin_radius or 0),
		"shift_type": r.shift_type,
		"strict": bool(r.enable_strict_geofence),
	}
