//: What the "Claimed hours" box holds before the person types: the day's cap, rounded DOWN to two
//: decimals. A Replacement Leave day carries the raw punch time ("8.876944444"), which read as a
//: stray number in the box, and rounding it up would offer time the cap check refuses. Overtime Pay
//: caps are already in 30-minute bands, so they come through unchanged (4.5 stays 4.5).
//: The 1e-9 keeps an exact 5.67 (566.9999… after * 100) from dropping to 5.66.
export const prefillClaim = (cap) => {
	const hours = Number(cap)
	if (!Number.isFinite(hours) || hours <= 0) return hours
	return Math.floor(hours * 100 + 1e-9) / 100
}

//: What Claimed hours holds once the picked day's check answers: what is already there (a
//: saved claim reopened), else what was kept across a reload of the same day, else the day's
//: cap. "" counts as nothing: the Hours row mounts when a day is picked and seeds "" before the
//: check answers, and `??` kept that "" (27 Oct 2026, the box stayed empty).
const isBlank = (value) => value == null || value === ""
export const claimAfterCheck = ({ current, retained, cap }) =>
	!isBlank(current) ? current : !isBlank(retained) ? retained : prefillClaim(cap)
