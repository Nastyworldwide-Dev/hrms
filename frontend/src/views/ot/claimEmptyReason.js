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
import { countOf } from "../../utils/countWords.js"

/** Whole half-day blocks a day's hours earn (4h = ½, 8h = 1 at the default). */
export function rlDaysFor(hours, hoursPerDay = 8) {
	const half = (hoursPerDay || 8) / 2
	if (!hours || half <= 0) return 0
	return Math.floor(hours / half) * 0.5
}

/**
 * "Days you can claim", shaped for display and sorted newest first:
 * - open days (Overtime Pay shows hours; Replacement Leave shows the whole-day
 *   blocks and DROPS days under the threshold — they earn nothing, per HR);
 * - days that already have a request, greyed, labelled by their decision;
 * - days worked but unclaimable (`incomplete`), greyed, with the reason under
 *   the date and an "HR can see this" tag. The employee still files their own
 *   request; the system just stops hiding the day. Nothing here asks them to
 *   fix a record.
 * opts: { isRL, rlHoursPerDay, translate, statusLabel(doc), formatHours(h) }
 */
export function claimDayRows(summary, opts = {}) {
	const { isRL = false, rlHoursPerDay = 8, statusLabel, formatHours } = opts
	const __ = opts.translate || ((text) => text)
	const hours = formatHours || ((h) => String(h))
	const days = summary?.days || []
	const claimedRows = summary?.claimed || []
	const brokenRows = summary?.incomplete || []
	console.info("[claimDayRows]", { days: days.length, incomplete: brokenRows.length })
	const open = !isRL
		? days.map((d) => ({ ...d, disabled: false, label: __("{0} h", [hours(d.hours)]) }))
		: days
				.map((d) => ({ ...d, leaveDays: rlDaysFor(d.hours, rlHoursPerDay) }))
				.filter((d) => d.leaveDays > 0)
				.map((d) => ({
					...d,
					disabled: false,
					label: __("{0} off", [countOf(d.leaveDays, __("day"))]),
				}))
	const claimed = claimedRows.map((d) => ({
		...d,
		claimed: true,
		disabled: true,
		label: __("Claimed · {0}", [__(statusLabel ? statusLabel(d) : d.status || "")]),
	}))
	const hrTag = __("HR can see this")
	const incomplete = brokenRows.map((d) => ({
		...d,
		incomplete: true,
		disabled: true,
		label: hrTag,
	}))
	return [...open, ...claimed, ...incomplete].sort((a, b) => b.date.localeCompare(a.date))
}

/**
 * The inline (red) error under Claimed hours. "Choose a work date" is not a
 * mistake the employee has made yet when the form has just opened, so it is
 * held back until they touch the date or try to save (E9-UX). Every error
 * that needs a date shows as soon as there is one.
 */
export function inlineClaimError(saveError, state = {}) {
	const { hasDate = false, touched = false, saveAttempted = false } = state
	if (!hasDate && !touched && !saveAttempted) return ""
	return saveError || ""
}

export function emptyClaimReason(summary, { isRL = false, rlHoursPerDay = 8, translate } = {}) {
	const __ = translate || ((text) => text)
	if (!summary) return ""

	const days = summary.days || []
	const half = (rlHoursPerDay || 8) / 2
	const incomplete = summary.incomplete || []
	console.info("[emptyClaimReason]", { isRL, days: days.length, incomplete: incomplete.length })

	if (isRL) {
		// Days exist but none reaches the threshold — the case worth explaining.
		const earning = days.filter((d) => rlDaysFor(d.hours, rlHoursPerDay) > 0)
		if (earning.length) return ""
		if (days.length)
			return __(
				"You have overtime on {0}, but replacement leave is earned in whole blocks — {1} h in a single day earns half a day off. None of these reach it.",
				[countOf(days.length, __("day")), half]
			)
	} else if (days.length) {
		return ""
	}

	// Only broken days in the list: say so, and that HR sees them — not "no
	// overtime recorded", which would read as "the system lost it".
	if (incomplete.length && !summary.days_already_claimed)
		return __(
			"Nothing to claim yet — {0} in this period have incomplete attendance records. HR can see these; you don't need to do anything.",
			[countOf(incomplete.length, __("day"))]
		)

	if (summary.days_already_claimed && !summary.days_with_overtime)
		return __("Every overtime day in this period has already been claimed.")
	if (summary.days_already_claimed)
		return __("Nothing left to claim — {0} in this period already have a request.", [
			countOf(summary.days_already_claimed, __("day")),
		])
	if (!summary.days_with_overtime)
		return __("No overtime recorded in this period, so there is nothing to claim yet.")
	return __("You worked overtime on {0} in this period, but none of it is claimable right now.", [
		countOf(summary.days_with_overtime, __("day")),
	])
}
