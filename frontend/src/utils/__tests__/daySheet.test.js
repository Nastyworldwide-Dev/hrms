// The Calendar day sheet (approved plan 01-calendar.md §4): exactly ONE main
// action, chosen by what the day needs, or none with one line saying so; hours
// as time, not decimals; taps as In / Out.
import { test } from "node:test"
import assert from "node:assert/strict"

import { dayAction, hoursAsTime, tapWord } from "../daySheet.js"

const TODAY = "2026-09-23"
const day = (over = {}) => ({
	date: "2026-09-10",
	status: "Present",
	worked_hours: 8,
	ot_hours: 0,
	punches: [{ log_type: "IN" }, { log_type: "OUT" }],
	shift: { start: "09:00", end: "18:00" },
	...over,
})

test("a normal worked day has no button: nothing to do", () => {
	assert.deepEqual(dayAction(day(), TODAY), { kind: "none", note: "Nothing to do." })
})

test("a day with overtime to claim offers the claim, with the hours", () => {
	assert.deepEqual(dayAction(day({ ot_hours: 1.5 }), TODAY), {
		kind: "claim",
		hours: 1.5,
		label: "Claim 1h 30m",
	})
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

test("a past day with punches and no attendance offers the fix", () => {
	// Owner bug, 23 Sep 2026: IN and OUT but no row read "Nothing to do." while
	// Requests said the same day had no attendance.
	const a = dayAction(day({ status: null, worked_hours: 0 }), TODAY)
	assert.equal(a.kind, "fix")
	assert.equal(a.label, "Fix this day")
})

test("today and future days are not asked to be fixed", () => {
	assert.equal(
		dayAction(day({ date: TODAY, status: null, punches: [{ log_type: "IN" }] }), TODAY).kind,
		"none"
	)
	assert.equal(
		dayAction(day({ date: "2026-09-30", status: null, punches: [] }), TODAY).kind,
		"none"
	)
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

test("a shift time reads HH:MM whatever the server sends", async () => {
	// Live audit 23 Sep: "9:00:–18:00". The server sends "9:00:00" (one-digit
	// hour); cutting at five characters kept the colon.
	const { clockTime } = await import("../daySheet.js")
	assert.equal(clockTime("9:00:00"), "09:00")
	assert.equal(clockTime("18:00:00"), "18:00")
	assert.equal(clockTime("07:30"), "07:30")
	assert.equal(clockTime(""), "")
	assert.equal(clockTime(null), "")
	// not a clock time: shown as nothing, never as garbage
	assert.equal(clockTime("1 day, 2:00:00"), "")
	assert.equal(clockTime("2026-09-10 09:00:00"), "")
})

test("no screen cuts a server time at five characters", async () => {
	const { readFileSync } = await import("node:fs")
	for (const file of [
		"../../components/DaySheet.vue",
		"../../views/team/TeamDashboard.vue",
		"../../components/NowBar.vue",
	]) {
		const source = readFileSync(new URL(file, import.meta.url), "utf8")
		assert.doesNotMatch(source, /\.slice\(0, 5\)/, `${file} slices a time`)
		assert.match(source, /clockTime\(/, `${file} reads times by value`)
	}
})
