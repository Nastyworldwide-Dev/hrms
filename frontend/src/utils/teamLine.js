// The Calendar day sheet's ONE team line (owner ruling 1, 23 Sep 2026;
// AUDIT-PLAN "Team line"). It is the door; the Team page is the room.
// Only non-zero parts show, and the words follow the day:
//   past    "Your team · 5 of 6 worked · 1 on leave"
//   today   "Your team · 4 of 6 in · 1 on leave · 1 not in yet"
//   future  "Your team · 2 on leave"
//   all in  "Your team · all 6 in"
export function teamLine(coverage, date, today, __) {
	const total = Number(coverage?.headcount) || 0
	if (!total) return ""
	const present = Number(coverage.present) || 0
	const onLeave = Number(coverage.on_leave) || 0
	const absent = Number(coverage.absent) || 0
	const unmarked = Number(coverage.unmarked) || 0
	const past = date < today
	const isToday = date === today

	const parts = [__("Your team")]
	if (isToday && present === total) return `${parts[0]} · ${__("all {0} in", [total])}`
	if (past && present) parts.push(__("{0} of {1} worked", [present, total]))
	if (isToday && present) parts.push(__("{0} of {1} in", [present, total]))
	if (onLeave) parts.push(__("{0} on leave", [onLeave]))
	// The Team page's own words, so the door and the room agree (review of
	// 391ccefbb): on a past day nobody-marked shows there as Absent ("No punch
	// · no leave filed"); today it is "Not in yet".
	if (isToday) {
		if (absent) parts.push(__("{0} absent", [absent]))
		if (unmarked) parts.push(__("{0} not in yet", [unmarked]))
	} else if (past && absent + unmarked) {
		parts.push(__("{0} absent", [absent + unmarked]))
	}
	return parts.length > 1 ? parts.join(" · ") : ""
}
