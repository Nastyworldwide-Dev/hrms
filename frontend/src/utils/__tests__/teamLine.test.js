// The Calendar day sheet's ONE team line (owner ruling 1, 23 Sep 2026;
// AUDIT-PLAN "Team line"). Only non-zero parts show; the words change with
// the day; the line is the door to the Team page for that date.
import { test } from "node:test"
import assert from "node:assert/strict"
import { teamLine } from "../teamLine.js"

const __ = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => String(args[i]))
const TODAY = "2026-09-23"

test("past day: 'Your team · 5 of 6 worked · 1 on leave'", () => {
	const line = teamLine(
		{ headcount: 6, present: 5, on_leave: 1, absent: 0, unmarked: 0 },
		"2026-09-22",
		TODAY,
		__
	)
	assert.equal(line, "Your team · 5 of 6 worked · 1 on leave")
})

test("today: 'Your team · 4 of 6 in · 1 on leave · 1 not in yet'", () => {
	const line = teamLine(
		{ headcount: 6, present: 4, on_leave: 1, absent: 0, unmarked: 1 },
		TODAY,
		TODAY,
		__
	)
	assert.equal(line, "Your team · 4 of 6 in · 1 on leave · 1 not in yet")
})

test("future day: 'Your team · 2 on leave'", () => {
	const line = teamLine(
		{ headcount: 6, present: 0, on_leave: 2, absent: 0, unmarked: 4 },
		"2026-09-30",
		TODAY,
		__
	)
	assert.equal(line, "Your team · 2 on leave")
})

test("everyone in: 'Your team · all 6 in'", () => {
	const line = teamLine(
		{ headcount: 6, present: 6, on_leave: 0, absent: 0, unmarked: 0 },
		TODAY,
		TODAY,
		__
	)
	assert.equal(line, "Your team · all 6 in")
})

test("a past day with people nobody marked says so", () => {
	const line = teamLine(
		{ headcount: 6, present: 3, on_leave: 0, absent: 1, unmarked: 2 },
		"2026-09-22",
		TODAY,
		__
	)
	assert.equal(line, "Your team · 3 of 6 worked · 1 absent · 2 not marked")
})

test("no team, no line", () => {
	assert.equal(teamLine(null, TODAY, TODAY, __), "")
	assert.equal(teamLine({ headcount: 0 }, TODAY, TODAY, __), "")
})

test("the Team page opens on the day the line summarised", async () => {
	const { readFileSync } = await import("node:fs")
	const page = readFileSync(new URL("../../views/team/TeamDashboard.vue", import.meta.url), "utf8")
	assert.match(page, /dateFromRoute\(route\.query\)/)
	assert.match(page, /ref\(askedDate \|\| /)
})

test("the Team page starts with the names, not a four-tile strip (no repeat)", async () => {
	// AUDIT-PLAN "Team line": the day sheet's line is the summary; the
	// Team page's In / On leave / Absent / Not marked strip is cut.
	const { readFileSync } = await import("node:fs")
	const page = readFileSync(new URL("../../views/team/TeamDashboard.vue", import.meta.url), "utf8")
	assert.doesNotMatch(page, /<GStatPanel|summaryTiles/)
})
