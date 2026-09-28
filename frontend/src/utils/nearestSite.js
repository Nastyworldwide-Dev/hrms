// The site the check-in screen should measure against (28 Sep 2026: HR can let
// a person check in at more than one site). Mirrors the server's rule in
// hrms/utils/geofence.py evaluate_sites: a free site or a site the person is
// inside wins; otherwise the nearest. The server still decides; this only keeps
// the screen's "You're at …" and distance in step with it.
//
// `loc` is get_active_shift_location's payload (main site + `other_sites`);
// `here` is {latitude, longitude} or null; `metres(a, b)` measures two points.
// Returns the main payload with the chosen site's place fields laid over it.

import { validCoordinates } from "./geolocation.js"

//: A site with no usable pin is infinitely far, as the server scores it
//: (evaluate_sites: distance None -> inf). Without this a missing pin measured
//: as NaN and the nearest-site pick locked onto it (review of c00dd370e).
function distance(site, here, metres) {
	const d = validCoordinates(site.latitude, site.longitude) ? metres(site, here) : Infinity
	return Number.isFinite(d) ? d : Infinity
}

export function nearestSite(loc, here, metres) {
	const others = loc?.other_sites || []
	if (!others.length || !here) return loc
	const candidates = [loc, ...others]
	const inside = candidates.find(
		(site) =>
			site.free_location ||
			(site.checkin_radius > 0 && distance(site, here, metres) <= site.checkin_radius)
	)
	let chosen = inside
	if (!chosen) {
		let best = Infinity
		for (const site of candidates) {
			const d = distance(site, here, metres)
			if (d < best) [best, chosen] = [d, site]
		}
		chosen = chosen || loc
	}
	// debug, not info: this runs on every location tick (review of c00dd370e)
	console.debug("[nearestSite]", chosen.shift_location, inside ? "inside" : "nearest")
	if (chosen === loc) return loc
	return {
		...loc,
		shift_location: chosen.shift_location,
		label: chosen.label,
		latitude: chosen.latitude,
		longitude: chosen.longitude,
		checkin_radius: chosen.checkin_radius,
		free_location: chosen.free_location,
		has_shift_location: true,
	}
}
