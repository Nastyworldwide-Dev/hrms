// Which legend keys a month shows (approved Calendar plan, C6): only the
// states the month has, in the legend's own fixed order.
import { test } from "node:test"
import assert from "node:assert/strict"

import { legendFor } from "../calendarLegend.js"

const all = [
	{ state: "present", label: "Worked" },
	{ state: "half", label: "Half day" },
	{ state: "leave", label: "Leave" },
	{ state: "rest", label: "Rest day" },
	{ state: "absent", label: "Absent" },
]

// SUPERSEDED by owner ruling R1 (23 Sep 2026): "always show every kind".
// A key that changes month to month has to be re-read every month; one that
// never changes is learned once (WCAG 1.4.1: colour always has its word).
test("every kind, every month, in the legend's order", () => {
	const days = [{ state: "absent" }, { state: "present" }, { state: "none" }]
	assert.deepEqual(
		legendFor(all, days).map((k) => k.state),
		["present", "half", "leave", "rest", "absent"]
	)
})

test("an empty month still shows the whole key", () => {
	assert.equal(legendFor(all, [{ state: "none" }]).length, all.length)
})
