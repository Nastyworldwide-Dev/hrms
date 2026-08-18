"""Geofence decision logic for Employee Checkin.

Pure helper called from `hrms.overrides.employee_checkin_override.CustomEmployeeCheckin
.validate_distance_from_shift_location`. Keeps the branching out of the
Frappe-bound override so it can be unit-tested without a DB.

Decision rules (see Shift Assignment.enable_strict_geofence):
    Lenient mode (default):
      - No shift location on assignment   -> allow (None)
      - Radius <= 0                       -> allow (None)
      - Inside radius                     -> allow (None)
      - Outside radius                    -> require_remote (flag for approval)

    Strict mode:
      - No shift location on assignment   -> throw (no_shift_location)
      - Radius <= 0                       -> throw (no_radius)
      - Inside radius                     -> allow (None)
      - Outside radius                    -> throw (outside_radius)

Public API:
    evaluate_geofence(strict, has_shift_location, radius_m, distance_m)
        -> None | (action, context)

        action is one of: "throw", "require_remote"
        context carries the data the caller needs to log + build messages.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

GeofenceDecision = tuple[str, dict] | None

REASON_NO_SHIFT_LOCATION = "no_shift_location"
REASON_NO_RADIUS = "no_radius"
REASON_OUTSIDE_RADIUS = "outside_radius"


def evaluate_geofence(
	strict: bool,
	has_shift_location: bool,
	radius_m: int,
	distance_m: float | None,
) -> GeofenceDecision:
	"""Decide how to handle a check-in given its geofence inputs.

	Returns None to allow, or a (action, context) tuple where action is
	"throw" (raise CheckinRadiusExceededError) or "require_remote" (flag
	the doc so the after_insert hook spawns a Remote Checkin Request).
	"""
	if not has_shift_location:
		if strict:
			logger.info("[geofence] strict throw — no shift location on assignment")
			return ("throw", {"reason": REASON_NO_SHIFT_LOCATION})
		return None

	if radius_m is None or radius_m <= 0:
		if strict:
			logger.info("[geofence] strict throw — radius<=0 (got %r)", radius_m)
			return ("throw", {"reason": REASON_NO_RADIUS})
		return None

	if distance_m is None:
		# Defensive: caller should always provide distance when shift loc is set.
		# Treat as if outside radius — strict throws, lenient routes to remote.
		distance_m = float("inf")

	if distance_m <= radius_m:
		return None

	overshoot = max(0.0, distance_m - radius_m)
	context = {
		"reason": REASON_OUTSIDE_RADIUS,
		"distance_m": distance_m,
		"radius_m": radius_m,
		"overshoot_m": overshoot,
	}
	if strict:
		logger.info(
			"[geofence] strict throw — outside radius distance=%.1fm radius=%dm",
			distance_m,
			radius_m,
		)
		return ("throw", context)

	logger.info(
		"[geofence] route to remote approval — distance=%.1fm radius=%dm",
		distance_m,
		radius_m,
	)
	return ("require_remote", context)


#: Fields the geofence decision needs off the Shift Assignment in force.
_ASSIGNMENT_FIELDS = ("name", "shift_type", "shift_location", "enable_strict_geofence")


def resolve_assignment(employee: str, at, shift_type: str | None = None):
	"""The Shift Assignment whose geofence policy governs a punch, or None.

	ONE query, shared by the preflight (`hrms.api.geofence.check_geofence`) and
	the enforcing insert (`CustomEmployeeCheckin`). They used to run two
	different ones and disagree in a way that always favoured the attacker:

	* the insert filtered on `shift_location is set`. `enable_strict_geofence`
	  is read off the row that filter selects, so an assignment with strict ON
	  and NO location matched nothing, `strict` fell back to False, and the
	  "strict + no shift location -> throw" rule in `evaluate_geofence` was
	  unreachable from the only path that can actually stop a check-in;
	* the preflight did not filter on it, so the PWA refused the very punch the
	  API accepted.

	The location filter is therefore gone: the row is selected on the shift
	policy alone and `evaluate_geofence` decides what a missing location means.

	`shift_type` narrows to the shift the check-in already resolved. The
	preflight has not resolved one yet and passes None; with overlapping
	assignments across shift types it may therefore preview a different
	assignment than the insert enforces. That is inherent to previewing a punch
	before its shift is known, and it is advisory either way — the insert is
	authoritative.

	`frappe` is imported inside the function so this module stays importable,
	and unit-testable, without a bench.
	"""
	import frappe

	filters = {
		"employee": employee,
		"start_date": ["<=", at],
		"docstatus": 1,
		"status": "Active",
	}
	if shift_type:
		filters["shift_type"] = shift_type

	rows = frappe.get_all(
		"Shift Assignment",
		filters=filters,
		or_filters=[["end_date", ">=", at], ["end_date", "is", "not set"]],
		fields=list(_ASSIGNMENT_FIELDS),
		order_by="start_date desc",
		limit=1,
	)
	return rows[0] if rows else None


def resolve_location(shift_location: str | None):
	"""The Shift Location row a geofence measures against, or None."""
	if not shift_location:
		return None
	import frappe

	return frappe.db.get_value(
		"Shift Location",
		shift_location,
		["checkin_radius", "latitude", "longitude"],
		as_dict=True,
	)
