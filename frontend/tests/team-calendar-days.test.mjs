// The Team page picks its day from a month calendar (the Attendance
// calendar card, reused). The grid marks ONLY the selected day and today —
// a team has no single per-day status to tint, so no day may carry a
// present/leave/absent state. Run: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"

import { buildTeamCalendarDays } from "../src/utils/team.js"

test("one cell per day of the month, selected day marked, the rest plain", () => {
	const days = buildTeamCalendarDays("2026-09-01", "2026-09-08", "2026-09-30")
	assert.equal(days.length, 30)
	assert.deepEqual(days[7], { day: 8, state: "selected" })
	assert.ok(days.filter((d) => d.state !== "none").length === 2)
	assert.deepEqual(days[29], { day: 30, state: "today" })
})

test("selected day outside the shown month marks nothing", () => {
	const days = buildTeamCalendarDays("2026-08-01", "2026-09-08", "2026-09-30")
	assert.equal(days.length, 31)
	assert.ok(days.every((d) => d.state === "none"))
})

test("selected day wins over today when they coincide", () => {
	const days = buildTeamCalendarDays("2026-09-01", "2026-09-30", "2026-09-30")
	assert.deepEqual(days[29], { day: 30, state: "selected" })
})
