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
