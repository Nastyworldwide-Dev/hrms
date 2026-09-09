// Geolocation facts that are the same on every platform, kept out of the
// check-in panel so they can be tested without a browser.
//
// The panel used to explain a failed fix by printing the raw
// GeolocationPositionError, and its comments discussed Android as though it
// were the only device in the building. It is not: staff punch in from
// iPhones and iPads, and from desktops that have no radio at all and locate
// themselves by asking the network where their IP lives. All three fail here
// in different ways, and only one of those failures is anything the employee
// can act on.

export const GEO_UNSUPPORTED = "unsupported"
export const GEO_INSECURE = "insecure"
export const GEO_DENIED = "denied"
export const GEO_UNAVAILABLE = "unavailable"
export const GEO_TIMEOUT = "timeout"

/**
 * Why this page cannot geolocate at all, before any fix is requested.
 * Returns null when it can.
 */
export function geolocationBlockedReason(win) {
	const target = win || (typeof window !== "undefined" ? window : null)
	if (!target || !target.navigator || !target.navigator.geolocation) {
		return GEO_UNSUPPORTED
	}
	// Every current browser refuses geolocation outside a secure context and
	// reports it as PERMISSION_DENIED — indistinguishable from the employee
	// having said no. Staff reaching the site over http://<lan-ip>:8000, which
	// is how a desk browser usually gets to a bench, were told to check their
	// browser permissions, and no amount of checking could ever fix it.
	if (target.isSecureContext === false) {
		return GEO_INSECURE
	}
	return null
}

/**
 * Classify a GeolocationPositionError into something worth telling a person.
 */
export function describeGeolocationError(error) {
	switch (error?.code) {
		case 1:
			return GEO_DENIED
		case 3:
			return GEO_TIMEOUT
		default:
			// POSITION_UNAVAILABLE, and anything a browser invents later.
			return GEO_UNAVAILABLE
	}
}

/**
 * The device's error estimate, as a person-readable radius.
 * `null` for a reading that carries no estimate.
 */
export function formatAccuracy(accuracyM) {
	const m = Number(accuracyM)
	if (!Number.isFinite(m) || m <= 0) return null
	if (m >= 1000) return `±${(m / 1000).toFixed(1)} km`
	return `±${Math.round(m)} m`
}

// Whether an incoming GPS reading should replace the one we are holding.
// watchPosition streams readings as the fix refines AND drifts, so we keep the
// SHARPEST (lowest accuracy in metres), not merely the latest — otherwise a
// later, worse reading places a stationary user "outside" their own office (the
// 102 m-from-Damansara report). Correct for the short, stationary check-in/out
// window. Unknown incoming accuracy never displaces a real fix; the first
// reading is always taken so the map can center.
export function shouldReplaceFix(currentAccuracyM, incomingAccuracyM, hasFix) {
	if (!hasFix) return true
	if (incomingAccuracyM == null) return false
	return currentAccuracyM == null || incomingAccuracyM <= currentAccuracyM
}

// The exception to sharpest-wins: watchPosition's first reading can be a CACHED
// fix up to maximumAge old (60s). If that cached fix is sharp, shouldReplaceFix
// would keep it and reject every fresher live reading, pinning a user who has
// since moved at their old spot. A reading this much newer than the one we hold
// wins on freshness regardless of accuracy. Pure, so it is testable without GPS.
export function preferFreshFix(currentFixAtMs, incomingAtMs, staleMs) {
	if (currentFixAtMs == null || incomingAtMs == null) return false
	return incomingAtMs - currentFixAtMs > staleMs
}

export const MAX_FIX_AGE_MS = 60000

export function validCoordinates(latitude, longitude) {
	return (
		Number.isFinite(latitude) &&
		Math.abs(latitude) <= 90 &&
		Number.isFinite(longitude) &&
		Math.abs(longitude) <= 180
	)
}

// Browser timestamps are evidence, not an arrival time. Never relabel a cached
// or malformed reading as fresh merely because its callback arrived just now.
export function usablePosition(position, now = Date.now()) {
	const coords = position?.coords
	const timestamp = position?.timestamp
	if (
		!coords ||
		!validCoordinates(coords.latitude, coords.longitude) ||
		!Number.isFinite(timestamp) ||
		timestamp > now ||
		now - timestamp > MAX_FIX_AGE_MS ||
		(coords.accuracy != null && (!Number.isFinite(coords.accuracy) || coords.accuracy < 0))
	) {
		console.warn("[geolocation] discarded invalid or expired device reading")
		return null
	}
	return {
		latitude: coords.latitude,
		longitude: coords.longitude,
		accuracy: coords.accuracy ?? null,
		timestamp,
	}
}

// Mirrors hrms.utils.geofence.evaluate_geofence; executable cross-language
// boundary tests keep the written preview aligned with authoritative enforcement.
export function previewGeofence({ strict, hasLocation, radius, distance, accuracy, freeLocation }) {
	if (freeLocation) {
		// Mirrors the server: a free Shift Location has no fence, strict or not.
		console.debug("[geolocation] preview decision", "allow", "free_location")
		return { action: "allow", reason: "free_location" }
	}
	const error = Number(accuracy) > 0 ? Number(accuracy) : 0
	const metres = Number.isFinite(distance) ? distance : Infinity
	let reason = null
	if (!hasLocation) reason = "no_shift_location"
	else if (!(radius > 0)) reason = "no_radius"
	else if (error > 250 && !(metres <= radius && error <= 2000)) reason = "imprecise_location"
	else if (metres > radius + error) reason = "outside_radius"
	const unchecked = reason === "no_shift_location" || reason === "no_radius"
	const action = !reason || (unchecked && !strict) ? "allow" : strict ? "throw" : "require_remote"
	console.debug("[geolocation] preview decision", action, reason)
	return { action, reason }
}
