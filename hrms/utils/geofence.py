"""Geofence decision logic for Employee Checkin.

Pure helper called from `hrms.overrides.employee_checkin_override.CustomEmployeeCheckin
.validate_distance_from_shift_location`. Keeps the branching out of the
Frappe-bound override so it can be unit-tested without a DB.

Decision rules (see Shift Assignment.enable_strict_geofence):
    Lenient mode (default):
      - No shift location on assignment   -> allow (None)
      - Radius <= 0                       -> allow (None)
      - Reading too imprecise to place    -> require_remote (imprecise_location)
      - Inside radius + accuracy          -> allow (None)
      - Outside radius + accuracy         -> require_remote (flag for approval)

    Strict mode:
      - No shift location on assignment   -> throw (no_shift_location)
      - Radius <= 0                       -> throw (no_radius)
      - Reading too imprecise to place    -> throw (imprecise_location)
      - Inside radius + accuracy          -> allow (None)
      - Outside radius + accuracy         -> throw (outside_radius)

"accuracy" is the device's own error estimate for the fix it just handed us
(`GeolocationCoordinates.accuracy`, metres, 95% confidence). It is not a
detail: the radius is tens of metres and the estimate routinely exceeds it.
A phone indoors, an iPad on wifi and a desktop with no radio at all report
wildly different confidence in coordinates that all arrive looking equally
exact, and until this argument existed all three were measured as if they
were surveyed points.

Public API:
    evaluate_geofence(strict, has_shift_location, radius_m, distance_m,
                      accuracy_m=None)
        -> None | (action, context)

        action is one of: "throw", "require_remote"
        context carries the data the caller needs to log + build messages.
        accuracy_m=None means "unknown" and buys no allowance — the pre-
        accuracy behaviour, which is what biometric device punches and any
        Desk-entered row still get.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

GeofenceDecision = tuple[str, dict] | None

REASON_NO_SHIFT_LOCATION = "no_shift_location"
REASON_NO_RADIUS = "no_radius"
REASON_OUTSIDE_RADIUS = "outside_radius"
REASON_IMPRECISE_LOCATION = "imprecise_location"

#: How much slack a device's own accuracy estimate may buy it, in metres.
#: A handset reporting +/-40 m gets the radius widened by 40 m: it is standing
#: where it says it is, to the best of what it can measure, and the fence is
#: not there to punish it for being indoors.
#:
#: Past this, the number stops describing a position. A desktop with no radio
#: geolocates by IP and reports kilometres; so does a phone that fell back to
#: the network provider. Widening a 50 m fence by 5 km would not be lenient,
#: it would delete the fence — and *narrowing* it is no better, because the
#: coordinate it would reject is not evidence of anything either. Neither
#: answer is available from the data, so the reading is refused as a reading
#: and the punch is put in front of whoever the shift's rules put there.
#:
#: ponytail: one constant for every company. Make it a per-company HR Setting
#: if a site's device fleet genuinely needs a different ceiling.
ACCURACY_ALLOWANCE_CAP_M = 250


def usable_accuracy(accuracy_m) -> float:
	"""The device's error estimate as a non-negative float, 0.0 if unusable."""
	# Callers hand this straight off an HTTP request, so it arrives as a string,
	# as None, or as junk. Anything unreadable is treated as "unknown", which
	# buys no allowance — never as 0 metres of error, which would buy trust.
	try:
		accuracy = float(accuracy_m) if accuracy_m not in (None, "") else 0.0
	except (TypeError, ValueError):
		logger.info("[geofence] unreadable accuracy %r — treated as unknown", accuracy_m)
		accuracy = 0.0
	return accuracy if accuracy > 0 else 0.0


def evaluate_geofence(
	strict: bool,
	has_shift_location: bool,
	radius_m: int,
	distance_m: float | None,
	accuracy_m: float | None = None,
) -> GeofenceDecision:
	"""Decide how to handle a check-in given its geofence inputs."""
	# Returns None to allow, or a (action, context) tuple where action is
	# "throw" (raise CheckinRadiusExceededError) or "require_remote" (flag
	# the doc so the after_insert hook spawns a Remote Checkin Request).
	logger.info(
		"[geofence] evaluate strict=%s has_loc=%s radius=%r distance=%r accuracy=%r",
		strict,
		has_shift_location,
		radius_m,
		distance_m,
		accuracy_m,
	)
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

	accuracy = usable_accuracy(accuracy_m)
	context = {
		"reason": REASON_OUTSIDE_RADIUS,
		"distance_m": distance_m,
		"radius_m": radius_m,
		"overshoot_m": max(0.0, distance_m - radius_m),
		"accuracy_m": accuracy,
	}

	if accuracy > ACCURACY_ALLOWANCE_CAP_M:
		# The fix is too coarse to place anyone. Note this runs BEFORE the
		# inside-radius test on purpose: a reading this vague cannot clear the
		# fence any more than it can fail it, and letting it clear the fence is
		# the direction that gets abused — an IP-geolocated desktop anywhere in
		# the city reports coordinates near the city centre, which is "inside"
		# for any site near it, by luck rather than by presence.
		context["reason"] = REASON_IMPRECISE_LOCATION
		if strict:
			logger.info(
				"[geofence] strict throw — accuracy %.0fm exceeds the %dm cap (distance=%.1fm)",
				accuracy,
				ACCURACY_ALLOWANCE_CAP_M,
				distance_m,
			)
			return ("throw", context)
		logger.info(
			"[geofence] route to remote approval — accuracy %.0fm exceeds the %dm cap",
			accuracy,
			ACCURACY_ALLOWANCE_CAP_M,
		)
		return ("require_remote", context)

	# The device's own error bar widens the fence. Everything inside the sum is
	# somewhere the employee could genuinely be standing while the reading says
	# what it says, and a fence that rejects those is measuring the receiver,
	# not the person.
	if distance_m <= radius_m + accuracy:
		return None

	if strict:
		logger.info(
			"[geofence] strict throw — outside radius distance=%.1fm radius=%dm accuracy=%.0fm",
			distance_m,
			radius_m,
			accuracy,
		)
		return ("throw", context)

	logger.info(
		"[geofence] route to remote approval — distance=%.1fm radius=%dm accuracy=%.0fm",
		distance_m,
		radius_m,
		accuracy,
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
