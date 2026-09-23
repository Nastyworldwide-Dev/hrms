// The Calendar day sheet (approved plan 01-calendar.md §4): exactly ONE main
// action, chosen by what the day needs, or none with one line saying so; hours
// as time, not decimals; taps as In / Out.
import { test } from "node:test"
import assert from "node:assert/strict"

import { dayAction, hoursAsTime, tapWord } from "../daySheet.js"

const TODAY = "2026-09-23"
const day = (over = {}) => ({ date: "2026-09-10", status: "Present", worked_hours: 8, ot_hours: 0, punches: [{ log_type: "IN" }, { log_type: "OUT" }], shift: { start: "09:00", end: "18:00" }, ...over })

test("a normal worked day has no button: nothing to do", () => {
	assert.deepEqual(dayAction(day(), TODAY), { kind: "none", note: "Nothing to do." })
})

test("a day with overtime to claim offers the claim, with the hours", () => {
	assert.deepEqual(dayAction(day({ ot_hours: 1.5 }), TODAY), { kind: "claim", hours: 1.5, label: "Claim 1h 30m" })
})

test("a lone check-in asks when you left", () => {
	const a = dayAction(day({ punches: [{ log_type: "IN" }] }), TODAY)
	assert.equal(a.kind, "fix")
	assert.equal(a.label, "Tell us when you left")
})

test("an absent work day offers a fix", () => {
	const a = dayAction(day({ status: "Absent", worked_hours: 0, punches: [] }), TODAY)
	assert.equal(a.kind, "fix")
	assert.equal(a.label, "Fix this day")
})

test("leave and rest days need nothing", () => {
	assert.equal(dayAction(day({ status: "On Leave", punches: [] }), TODAY).kind, "none")
	assert.equal(dayAction(day({ status: "Holiday", punches: [] }), TODAY).kind, "none")
})

test("today and future days are not asked to be fixed", () => {
	assert.equal(dayAction(day({ date: TODAY, status: null, punches: [{ log_type: "IN" }] }), TODAY).kind, "none")
	assert.equal(dayAction(day({ date: "2026-09-30", status: null, punches: [] }), TODAY).kind, "none")
})

test("hours read as time", () => {
	assert.equal(hoursAsTime(8.0333), "8h 02m")
	assert.equal(hoursAsTime(1.5), "1h 30m")
	assert.equal(hoursAsTime(0.25), "15m")
	assert.equal(hoursAsTime(0), "")
})

test("taps say In / Out, never the raw IN / OUT", () => {
	assert.equal(tapWord("IN"), "In")
	assert.equal(tapWord("OUT"), "Out")
	assert.equal(tapWord(null), "")
})
