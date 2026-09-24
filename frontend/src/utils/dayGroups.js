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
