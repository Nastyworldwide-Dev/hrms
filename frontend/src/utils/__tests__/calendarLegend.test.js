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

test("only the states this month has, in the legend's order", () => {
	const days = [{ state: "absent" }, { state: "present" }, { state: "none" }, { state: "present" }]
	assert.deepEqual(
		legendFor(all, days).map((k) => k.state),
		["present", "absent"]
	)
})

test("an empty month shows no legend", () => {
	assert.deepEqual(legendFor(all, [{ state: "none" }]), [])
})
