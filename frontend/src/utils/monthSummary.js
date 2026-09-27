// The Calendar's one-line month summary (alpha.13 slice 2), counted from the
// same `days` the grid draws, so the line and the tiles can never disagree.

const WORKED = new Set(["present", "half"])

//: { worked, toFix }, or null when the month has nothing to say yet.
//: Today while still in progress is not counted as worked until it closes.
export function monthSummary(days) {
	let worked = 0
	let toFix = 0
	for (const d of days || []) {
		if (WORKED.has(d.state)) worked += 1
		if ((d.flags || []).includes("needs_you")) toFix += 1
	}
	return worked || toFix ? { worked, toFix } : null
}
