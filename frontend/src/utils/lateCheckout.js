//: Where the Forgot to check out sheet starts (ticket #4855): 18:00 on the
//: check-in day, but never at or before the check-in and never in the future.
//: The bare 18:00 opened a 19:30 check-in's sheet red, with Send off, and
//: staff read that as the app freezing. Device clock, like the sheet's own
//: min/max (datetime-local is wall time).
//: Device wall time on purpose; the session rule in checkinSession.js reads the site clock.
export function defaultCheckoutTime(inTime, now = new Date()) {
	if (!inTime) return null
	const checkedIn = new Date(String(inTime).replace(" ", "T"))
	if (Number.isNaN(checkedIn.getTime())) return null
	const evening = new Date(checkedIn)
	evening.setHours(18, 0, 0, 0)
	const floor = new Date(checkedIn.getTime() + 60000)
	// Under a minute old: no valid minute exists yet, so leave it empty and let
	// the field ask "Pick the time you left." rather than offer a wrong time.
	if (floor > now) return null
	const start = evening > checkedIn ? evening : floor
	return start < now ? start : now
}
