// The shift gauge on Today (alpha.12, the owner's "Apple way" card).
// Pure: from the shift window and the minute of the day, never counted up, so
// it cannot drift while the phone sleeps (the same rule NowBar's elapsed uses).

//: Past the shift end by this much, an open check-in is probably a forgotten
//: check-out: the card asks. Three hours, as in the approved mockup.
export const FORGOT_AFTER_MIN = 180

const toMin = (hhmm) => {
	const [h, m] = String(hhmm || "").split(":").map(Number)
	return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null
}

//: { fraction 0..1, leftMin, pastMin, level: "working" | "past" | "forgot" },
//: or null when there is no shift window. A window whose end is at or before
//: its start crosses midnight (22:00-06:00).
export function shiftGauge({ start, end, nowMin }) {
	const s = toMin(start)
	let e = toMin(end)
	if (s === null || e === null) return null
	if (e <= s) e += 24 * 60
	let now = nowMin
	// on a night shift, the small hours belong to the shift that began last night
	if (e > 24 * 60 && now < s && now + 24 * 60 <= e + FORGOT_AFTER_MIN) now += 24 * 60
	const length = e - s
	const done = Math.min(Math.max(now - s, 0), length)
	const pastMin = Math.max(now - e, 0)
	const level = pastMin >= FORGOT_AFTER_MIN ? "forgot" : pastMin > 0 ? "past" : "working"
	return { fraction: done / length, leftMin: Math.max(e - now, 0), pastMin, level }
}
