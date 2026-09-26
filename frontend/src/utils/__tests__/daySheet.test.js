// The Calendar day sheet (approved plan 01-calendar.md §4): exactly ONE main
// action, chosen by what the day needs, or none with one line saying so; hours
// as time, not decimals; taps as In / Out.
import { test } from "node:test"
import assert from "node:assert/strict"

import { dayAction, dayStatusWord, hoursAsTime, tapWord } from "../daySheet.js"

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

// ------------------------------------------------ claim state (01-calendar §4 rows 3-5)

test("a claim waiting with an approver offers no second claim", () => {
	const a = dayAction(
		day({ ot_hours: 1.5, claim: { status: "Open", approver_name: "Hafiz" } }),
		TODAY
	)
	assert.deepEqual(a, { kind: "none", note: "Claim waiting with {0}", noteArgs: ["Hafiz"] })
})

test("a waiting claim with no named approver still says it is waiting", () => {
	const a = dayAction(day({ ot_hours: 1.5, claim: { status: "Open", approver_name: "" } }), TODAY)
	assert.deepEqual(a, { kind: "none", note: "Claim waiting" })
})

test("an approved claim says the overtime is claimed", () => {
	const a = dayAction(day({ ot_hours: 1.5, claim: { status: "Approved" } }), TODAY)
	assert.deepEqual(a, { kind: "none", note: "Overtime claimed" })
})

test("a rejected claim may be claimed again", () => {
	const a = dayAction(day({ ot_hours: 1.5, claim: { status: "Rejected" } }), TODAY)
	assert.deepEqual(a, { kind: "claim", hours: 1.5, label: "Claim again" })
})

// ------------------------------------------------ future day (01-calendar §4 row 13)

test("a future work day offers to ask for the day off", () => {
	const a = dayAction(day({ date: "2026-09-30", status: null, punches: [] }), TODAY)
	assert.deepEqual(a, { kind: "leave", label: "Ask for this day off" })
})

test("a future day already on leave, or a rest day, asks nothing", () => {
	const onLeave = day({ date: "2026-09-30", status: "On Leave", punches: [] })
	const rest = day({ date: "2026-09-30", status: "Holiday", punches: [] })
	assert.equal(dayAction(onLeave, TODAY).kind, "none")
	assert.equal(dayAction(rest, TODAY).kind, "none")
})

// ------------------------------------------------ status word (01-calendar §4 rule 1)

test("the heading's status word follows the day", () => {
	assert.equal(dayStatusWord(day(), TODAY), "Worked")
	assert.equal(dayStatusWord(day({ status: "Half Day" }), TODAY), "Worked")
	assert.equal(dayStatusWord(day({ status: "On Leave", punches: [] }), TODAY), "Leave")
	assert.equal(dayStatusWord(day({ status: "Holiday", punches: [] }), TODAY), "Rest day")
	assert.equal(dayStatusWord(day({ status: "Absent", punches: [] }), TODAY), "Absent")
	// "In progress" only while a check-in is open (owner, 26 Sep 2026: a date
	// holding only last night's check-out read as a day still being worked).
	const open = day({ date: TODAY, status: null, punches: [{ log_type: "IN" }] })
	assert.equal(dayStatusWord(open, TODAY), "In progress")
	const lastNight = day({ date: TODAY, status: null, punches: [{ log_type: "OUT" }] })
	assert.equal(dayStatusWord(lastNight, TODAY), "Today")
	const future = day({ date: "2026-09-30", status: null, punches: [] })
	assert.equal(dayStatusWord(future, TODAY), "Coming up")
})

test("a past day with nothing recorded has no status word", () => {
	assert.equal(dayStatusWord(day({ status: null, punches: [] }), TODAY), "")
})

test("today is not asked to be fixed", () => {
	assert.equal(
		dayAction(day({ date: TODAY, status: null, punches: [{ log_type: "IN" }] }), TODAY).kind,
		"none"
	)
	assert.notEqual(
		dayAction(day({ date: "2026-09-30", status: null, punches: [] }), TODAY).kind,
		"fix"
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
