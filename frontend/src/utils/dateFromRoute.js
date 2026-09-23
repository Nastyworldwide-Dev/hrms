// The day a form should start on, from its route (?date=YYYY-MM-DD). The
// Calendar day sheet sends it so "Fix this day" and "Claim" open on that day
// (approved Calendar plan, D2). Only a real calendar date is accepted: a URL
// is user input.
export function dateFromRoute(query) {
	const value = query?.date
	if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
	const [y, m, d] = value.split("-").map(Number)
	const date = new Date(Date.UTC(y, m - 1, d))
	const real =
		date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d
	if (!real) console.warn("[dateFromRoute] ignoring an impossible date", value)
	return real ? value : null
}
