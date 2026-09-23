// Which keys the Calendar shows. Owner ruling R1, 23 Sep 2026: the key ALWAYS
// shows every kind — it replaced the earlier "only the states this month has"
// (plan C6), because a key that changes month to month teaches nothing — plus
// Travel, Training and, for approvers only, Open request.
import { test } from "node:test"
import assert from "node:assert/strict"

import { legendFor } from "../calendarLegend.js"

const states = [
	{ state: "present", label: "Worked" },
	{ state: "half", label: "Half day" },
	{ state: "leave", label: "Leave" },
	{ state: "rest", label: "Rest day" },
	{ state: "absent", label: "Absent" },
]
const kinds = [
	{ state: "travel", label: "Travel" },
	{ state: "training", label: "Training" },
	{ state: "open", label: "Open request" },
]
const legend = [...states, ...kinds]

test("every kind is listed even in an empty month, in the key's own order", () => {
	assert.deepEqual(
		legendFor(legend, { flags: {}, approver: false }).map((k) => k.state),
		["present", "half", "leave", "rest", "absent", "travel", "training"]
	)
})

test("Open request is shown to an approver", () => {
	const keys = legendFor(legend, { flags: {}, approver: true }).map((k) => k.state)
	assert.equal(keys.at(-1), "open")
	assert.equal(keys.length, legend.length)
})

test("Open request is shown when the server sent an open flag", () => {
	const flags = { "2026-09-03": ["leave", "open"] }
	assert.ok(legendFor(legend, { flags, approver: false }).some((k) => k.state === "open"))
})

test("nobody else sees Open request", () => {
	const flags = { "2026-09-03": ["leave"] }
	assert.ok(!legendFor(legend, { flags, approver: false }).some((k) => k.state === "open"))
	assert.ok(!legendFor(legend, {}).some((k) => k.state === "open"))
})
