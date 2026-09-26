// Day groups for a time-ordered list (alpha.7 0.8): one heading per day,
// iOS style, instead of the day repeated on every row.
import dayjs from "dayjs"

//: Consecutive rows with the same day share a group; order is never changed.
export function groupByDay(rows, dayOf) {
	const groups = []
	for (const row of rows || []) {
		const day = dayOf(row)
		const last = groups[groups.length - 1]
		if (last && last.day === day) last.rows.push(row)
		else groups.push({ day, rows: [row] })
	}
	return groups
}

//: "Today", "Yesterday", "Tue 22 Sep", or "Wed 31 Dec 2025" in another year.
export function dayHeading(day, today) {
	const d = dayjs(day)
	const t = dayjs(today)
	if (d.isSame(t, "day")) return "Today"
	if (d.isSame(t.subtract(1, "day"), "day")) return "Yesterday"
	return d.format(d.isSame(t, "year") ? "ddd D MMM" : "ddd D MMM YYYY")
}

//: The work day of each tap, the server's rule (hrms/utils/work_day.py): a
//: tap's shift start date, else a check-out closes the day its check-in opened
//: (the next calendar day only), else the clock date. `rows` may be newest
//: first; the rule is read oldest first. Returns row -> "YYYY-MM-DD".
export function workDayOf(rows, clock = (value) => dayjs(value)) {
	const ymd = (value) => clock(value).format("YYYY-MM-DD")
	const ordered = [...(rows || [])].sort((a, b) => clock(a.time).valueOf() - clock(b.time).valueOf())
	const days = new Map()
	let openDay = null
	for (const row of ordered) {
		let day = row.shift_start ? ymd(row.shift_start) : ymd(row.time)
		if (!row.shift_start && row.log_type === "OUT" && openDay && dayjs(openDay).add(1, "day").format("YYYY-MM-DD") === day) {
			day = openDay
		}
		if (row.log_type === "IN") openDay = day
		else if (row.log_type === "OUT") openDay = null
		days.set(row, day)
	}
	return (row) => days.get(row) ?? ymd(row.time)
}
