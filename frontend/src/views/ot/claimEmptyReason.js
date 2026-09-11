// Why "Days you can claim" is empty, in one sentence.
//
// The list renders only when it has rows. With none, the form showed a blank
// date picker under the words "Choose a work date to check available overtime"
// — an instruction, not an answer. Four different situations looked identical
// on screen, and the employee was left to guess which one they were in.
//
// The replacement-leave case is the one nobody can work out alone: days DO
// exist, with real hours on them, and still earn nothing because each is under
// the half-day threshold. An empty screen reads as "the system lost my
// overtime".
//
// Kept free of Vue imports so it can be unit-tested under node.

/** Whole half-day blocks a day's hours earn (4h = ½, 8h = 1 at the default). */
export function rlDaysFor(hours, hoursPerDay = 8) {
	const half = (hoursPerDay || 8) / 2
	if (!hours || half <= 0) return 0
	return Math.floor(hours / half) * 0.5
}

export function emptyClaimReason(summary, { isRL = false, rlHoursPerDay = 8, translate } = {}) {
	const __ = translate || ((text) => text)
	if (!summary) return ""

	const days = summary.days || []
	const half = (rlHoursPerDay || 8) / 2

	if (isRL) {
		// Days exist but none reaches the threshold — the case worth explaining.
		const earning = days.filter((d) => rlDaysFor(d.hours, rlHoursPerDay) > 0)
		if (earning.length) return ""
		if (days.length)
			return __(
				"You have overtime on {0} day(s), but replacement leave is earned in whole blocks — {1} h in a single day earns half a day off. None of these reach it.",
				[days.length, half]
			)
	} else if (days.length) {
		return ""
	}

	if (summary.days_already_claimed && !summary.days_with_overtime)
		return __("Every overtime day in this period has already been claimed.")
	if (summary.days_already_claimed)
		return __("Nothing left to claim — {0} day(s) in this period already have a request.", [
			summary.days_already_claimed,
		])
	if (!summary.days_with_overtime)
		return __("No overtime recorded in this period, so there is nothing to claim yet.")
	return __(
		"You worked overtime on {0} day(s) in this period, but none of it is claimable right now.",
		[summary.days_with_overtime]
	)
}
