"""Geofence decision logic for Employee Checkin.

Pure helper called from `nsty.overrides.employee_checkin.CustomEmployeeCheckin
.validate_distance_from_shift_location`. Keeps the branching out of the
Frappe-bound override so it can be unit-tested without a DB.

Decision rules (see Shift Type.enable_strict_geofence):
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
