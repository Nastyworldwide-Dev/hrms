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
