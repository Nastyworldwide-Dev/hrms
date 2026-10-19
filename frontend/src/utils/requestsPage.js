// The Requests page on one phone screen (owner-approved layout, 23 Sep 2026).
// Kept free of Vue imports so node tests can run it.

//: The page shows this many of your own requests; the rest are behind See all.
export const LAST_ROWS = 5

//: A whole number reads as a count; 12.5 days is a real half-day balance.
export function trimNumber(value) {
	const n = Number(value)
	return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

//: "Annual Leave" -> "Annual". The line has room for two short names only.
//: A name that IS mostly "Leave" ("Leave Without Pay") keeps its words.
export function shortLeaveName(name = "") {
	return String(name).replace(/\s+leave$/i, "")
}

//: "Annual 6 · Medical 13" — the remaining balance of each pinned type.
export function balancesLine(rows = []) {
	const line = rows
		.map((row) => `${shortLeaveName(row.leave_type)} ${trimNumber(row.balance)}`)
		.join(" · ")
	console.info("[requestsPage] balances line", line)
	return line
}

//: The newest few of a list that is already sorted newest first.
export function lastRequests(requests) {
	return (requests || []).slice(0, LAST_ROWS)
}

//: Approvals links "Requests you've already answered" with ?tab=answered.
export function opensOnAnswered(query) {
	return query?.tab === "answered"
}

//: The All balances ring (owner pick B, 19 Oct 2026). One circle is the
//: year's entitlement: lime is what is left, grey what was taken, and
//: the rest (a mid-year joiner's never-given part, expired days) stays track.
//: Returns arc lengths for a circle of the given circumference.
export function ringArcs(row = {}, circumference = 1) {
	const whole = Number(row.total) || Number(row.allocated) || 0
	if (!whole) return { left: 0, taken: 0 }
	const share = (value) => Math.min(1, Math.max(0, (Number(value) || 0) / whole))
	const left = share(row.balance)
	const taken = Math.min(share(row.taken), 1 - left)
	return { left: left * circumference, taken: taken * circumference }
}
