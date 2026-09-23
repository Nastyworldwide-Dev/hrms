// The Calendar day sheet's rules (approved plan, docs/glass/plan/pages/
// 01-calendar.md §4). One main action per day, chosen by what the day needs,
// or none with one line saying so (mockup 4's openDay; Apple HIG: a sheet
// serves one focused task). The sheet used to offer "Request a fix" on every
// day, including perfect ones (D10).
//
// The words here are English source strings; the sheet translates them.

//: Statuses that mean the person was not expected to work that day.
const OFF = new Set(["On Leave", "Holiday"])

export function dayAction(day, today) {
	const past = day.date < today
	const taps = day.punches || []
	const lastTap = taps.at(-1)
	const loneIn = taps.length > 0 && lastTap?.log_type === "IN"

	// Today and future days: nothing is settled yet, so nothing is "wrong".
	if (!past) return { kind: "none", note: "" }
	// A check-in with no check-out: the day cannot be counted without it.
	if (loneIn) return { kind: "fix", label: "Tell us when you left" }
	if (day.ot_hours > 0) {
		return { kind: "claim", hours: day.ot_hours, label: `Claim ${hoursAsTime(day.ot_hours)}` }
	}
	if (day.status === "Absent") return { kind: "fix", label: "Fix this day" }
	if (OFF.has(day.status)) return { kind: "none", note: "" }
	return { kind: "none", note: "Nothing to do." }
}

//: "8h 02m", never "8.03 h": people read time in hours and minutes (D11).
export function hoursAsTime(hours) {
	const minutes = Math.round((Number(hours) || 0) * 60)
	if (minutes <= 0) return ""
	const h = Math.floor(minutes / 60)
	const m = minutes % 60
	if (!h) return `${m}m`
	return `${h}h ${String(m).padStart(2, "0")}m`
}

//: The person's words for a tap, not the stored IN / OUT (D12).
export function tapWord(logType) {
	if (logType === "IN") return "In"
	if (logType === "OUT") return "Out"
	return ""
}

//: "HH:MM" from a server time, whatever its width. The server sends "9:00:00"
//: for a one-digit hour; slicing five characters left "9:00:" (live audit,
//: 23 Sep). Read by value, not by position.
export function clockTime(value) {
	const [h, m] = String(value || "").split(":")
	if (!h || m === undefined) return ""
	return `${h.padStart(2, "0")}:${m.padStart(2, "0").slice(0, 2)}`
}
