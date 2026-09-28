// The site the check-in screen should measure against (28 Sep 2026: HR can let
// a person check in at more than one site). Mirrors the server's rule in
// hrms/utils/geofence.py evaluate_sites: a free site or a site the person is
// inside wins; otherwise the nearest. The server still decides; this only keeps
// the screen's "You're at …" and distance in step with it.
//
// `loc` is get_active_shift_location's payload (main site + `other_sites`);
// `here` is {latitude, longitude} or null; `metres(a, b)` measures two points.
// Returns the main payload with the chosen site's place fields laid over it.

export function nearestSite(loc, here, metres) {
	const others = loc?.other_sites || []
	if (!others.length || !here) return loc
	const candidates = [loc, ...others]
	const inside = candidates.find(
		(site) =>
			site.free_location || (site.checkin_radius > 0 && metres(site, here) <= site.checkin_radius)
	)
	const chosen =
		inside ||
		candidates.reduce((best, site) => (metres(site, here) < metres(best, here) ? site : best))
	console.info(
		"[nearestSite]",
		chosen.shift_location,
		inside ? "inside" : "nearest",
		"of",
		candidates.length
	)
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
