// When an open check-in stops being "still on shift" — the SERVER's rule
// (hrms.api.remote_checkin.session_open_until), read the same way here:
// 06:00 the morning after the check-in, or the shift's check-out window if that
// ends later. The button used its own 16-hour cap, so a 9 am check-in offered
// "Check in" again at 01:00 while the person was still working (employee
// report, 25 Sep 2026). Site-clock strings go through siteTime, never new Date.
import { siteTime } from "./siteTime.js"

export function sessionOpenUntil(inTime, shiftActualEnd) {
	const start = siteTime(inTime)
	if (!start.isValid()) return null
	let until = start.add(1, "day").hour(6).minute(0).second(0).millisecond(0)
	const windowEnd = shiftActualEnd ? siteTime(shiftActualEnd) : null
	if (windowEnd?.isValid() && windowEnd.isAfter(until)) until = windowEnd
	return until.valueOf()
}

export function sessionIsOpen(log, nowMs = Date.now()) {
	const until = sessionOpenUntil(log?.time, log?.shift_actual_end)
	return until !== null && nowMs < until
}

//: Where the Forgot to check out sheet starts (ticket #4855): 18:00 on the
//: check-in day, but never at or before the check-in and never in the future.
//: The bare 18:00 opened a 19:30 check-in's sheet red, with Send off, and
//: staff read that as the app freezing. Device clock, like the sheet's own
//: min/max (datetime-local is wall time).
export function defaultCheckoutTime(inTime, now = new Date()) {
	if (!inTime) return null
	const checkedIn = new Date(String(inTime).replace(" ", "T"))
	if (Number.isNaN(checkedIn.getTime())) return null
	const evening = new Date(checkedIn)
	evening.setHours(18, 0, 0, 0)
	const floor = new Date(checkedIn.getTime() + 60000)
	const start = evening > checkedIn ? evening : floor
	return start < now ? start : now
}
