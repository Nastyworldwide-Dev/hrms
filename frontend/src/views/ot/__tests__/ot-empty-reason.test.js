// An empty "Days you can claim" list must say WHY.
//
// Nabil, 11 Sep 2026: "why in my nadi pwa i see nothing to claim? idk which
// date i am eligble for claim. and what about those who are RL entitled?"
//
// The list renders only when it has rows. With none, the form showed a blank
// date picker under "Choose a work date to check available overtime" — an
// instruction, not an answer. Four different situations looked identical:
// everything already claimed, no overtime worked at all, overtime worked but
// capped, and the replacement-leave case where days DO exist with real hours
// and still earn nothing because each is under the half-day threshold.
//
// That last one is the one nobody can work out alone, and an empty screen reads
// as "the system lost my overtime".
import { test } from "node:test"
import assert from "node:assert/strict"

import { emptyClaimReason, rlDaysFor } from "../claimEmptyReason.js"

const __ = (text, args = []) => text.replace(/\{(\d+)\}/g, (_m, i) => args[i])

test("already claimed is named as such, not left blank", () => {
	const reason = emptyClaimReason(
		{ days: [], days_already_claimed: 3, days_with_overtime: 0, compensation: "Overtime Pay" },
		{ isRL: false, translate: __ }
	)
	assert.match(reason, /already/i)
})

test("no overtime worked says so plainly", () => {
	const reason = emptyClaimReason(
		{ days: [], days_already_claimed: 0, days_with_overtime: 0, compensation: "Overtime Pay" },
		{ isRL: false, translate: __ }
	)
	assert.match(reason, /no overtime/i)
})

test("replacement leave explains the threshold when every day falls under it", () => {
	const reason = emptyClaimReason(
		{
			days: [
				{ date: "2026-09-04", hours: 1.2 },
				{ date: "2026-09-07", hours: 2 },
			],
			days_already_claimed: 0,
			days_with_overtime: 2,
			compensation: "Replacement Leave",
		},
		{ isRL: true, rlHoursPerDay: 8, translate: __ }
	)
	assert.match(reason, /4 h/, "it must name the threshold")
	assert.match(reason, /half a day/i)
	assert.match(reason, /2 day/, "and say how many days it looked at")
})

test("days that DO reach the threshold produce no message at all", () => {
	const reason = emptyClaimReason(
		{
			days: [{ date: "2026-09-04", hours: 8 }],
			days_already_claimed: 0,
			days_with_overtime: 1,
			compensation: "Replacement Leave",
		},
		{ isRL: true, rlHoursPerDay: 8, translate: __ }
	)
	assert.equal(reason, "", "there is something to claim — the list speaks for itself")
})

test("overtime worked but nothing claimable is not silently blank", () => {
	const reason = emptyClaimReason(
		{ days: [], days_already_claimed: 1, days_with_overtime: 4, compensation: "Overtime Pay" },
		{ isRL: false, translate: __ }
	)
	assert.ok(reason.length > 0)
})

test("a summary that has not loaded says nothing rather than guessing", () => {
	assert.equal(emptyClaimReason(null, { isRL: false, translate: __ }), "")
	assert.equal(emptyClaimReason(undefined, { isRL: false, translate: __ }), "")
})

test("the half-day ladder matches HR's rule", () => {
	// 4h = half, 8h = one, 12h = one and a half, under 4h earns nothing.
	assert.equal(rlDaysFor(3.99, 8), 0)
	assert.equal(rlDaysFor(4, 8), 0.5)
	assert.equal(rlDaysFor(8, 8), 1)
	assert.equal(rlDaysFor(12, 8), 1.5)
})
