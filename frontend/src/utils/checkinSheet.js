// The words a check-in sheet shows (alpha.14 A). Read from the outcome the
// server stored on the punch (employee_checkin_override.py), never recomputed
// here.
import { isReadingCoarse } from "./geolocation.js"

const OUTCOME_WORDS = {
	Inside: "Inside the work area",
	Outside: "Outside the work area",
	Imprecise: "Location too rough to place",
	"Free Location": "Anywhere allowed",
	"No Shift": "No shift that day",
	"No Location": "No work area set",
	"No Radius": "No work area set",
	"Tracking Off": "Location was off",
	"Late Checkout": "Added later (forgot to check out)",
	"Manual Entry": "Added by HR",
}
const WITH_DISTANCE = new Set(["Inside", "Outside"])

function distance(metres) {
	const m = Number(metres)
	if (!Number.isFinite(m)) return ""
	return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`
}

export function whereLine(punch) {
	const words = OUTCOME_WORDS[punch?.geofence_outcome]
	if (!words) return ""
	// a coarse fix cannot support a figure (RemoteCheckinDialog hides it too)
	const d =
		WITH_DISTANCE.has(punch.geofence_outcome) && !isReadingCoarse(punch.location_accuracy_m)
			? distance(punch.geofence_distance_m)
			: ""
	return d ? `${words} · ${d}` : words
}

//: For tracing a problem (owner, 27 Sep 2026): kept, but quiet. A missing
//: reading is nothing, not 0.00000 or NaN.
export function coordinateLine(punch) {
	const lat = Number(punch?.latitude)
	const lng = Number(punch?.longitude)
	if (!Number.isFinite(lat) || !Number.isFinite(lng) || punch.latitude == null || punch.longitude == null) return ""
	if (lat === 0 && lng === 0) return ""
	return `${lat.toFixed(5)}, ${lng.toFixed(5)}`
}
