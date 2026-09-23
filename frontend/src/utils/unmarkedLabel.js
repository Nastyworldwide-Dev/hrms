// The Requests row for days with no attendance (owner bug, 23 Sep 2026).
// "1 day with no attendance" named no day, so nobody could tell which one to
// fix. The row now names it — "Wed 16 Sep has no attendance" — and a tap opens
// that day on the Calendar, where the day sheet offers the fix.
//
// Dates are read as calendar dates (UTC midnight), never through the local
// clock, so the weekday cannot slip a day in another time zone.

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
//: More dates than this and the row stops fitting one line on a phone.
const SHOWN = 3

function parts(iso) {
	const [y, m, d] = iso.split("-").map(Number)
	const date = new Date(Date.UTC(y, m - 1, d))
	return { weekday: WEEKDAYS[date.getUTCDay()], day: d, month: MONTHS[m - 1] }
}

//: "16, 18 Sep" — the month once per run of days in it.
function dateList(dates) {
	const shown = dates.slice(0, SHOWN).map(parts)
	const text = shown
		.map((p, i) => (shown[i + 1]?.month === p.month ? `${p.day}` : `${p.day} ${p.month}`))
		.join(", ")
	return dates.length > SHOWN ? `${text}…` : text
}

export function unmarkedLabel(attendance, __) {
	const dates = attendance?.dates || []
	const count = attendance?.days || dates.length
	if (count === 1 && dates.length === 1) {
		const p = parts(dates[0])
		return __("{0} has no attendance", [`${p.weekday} ${p.day} ${p.month}`])
	}
	const head = __("{0} days have no attendance", [count])
	return dates.length ? `${head} · ${dateList(dates)}` : head
}

//: The Calendar, open on the first day that needs a fix.
export function unmarkedRoute(attendance) {
	const first = attendance?.dates?.[0]
	console.info("[unmarkedLabel] opening the calendar", first || "(no date)")
	return first ? { name: "AttendanceDashboard", query: { date: first } } : { name: "AttendanceDashboard" }
}
