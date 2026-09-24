// alpha.7 4.4/4.5: which must-read opens full screen, and what its buttons do.
import { test } from "node:test"
import assert from "node:assert/strict"
import { nextMustRead, confirmState } from "../mustRead.js"

const q = [
	{ name: "U", urgent: 1 },
	{ name: "A", urgent: 0 },
	{ name: "B", urgent: 0 },
]

test("the first notice not put off opens; urgent ones cannot be put off", () => {
	assert.equal(nextMustRead(q, new Set()).name, "U")
	assert.equal(nextMustRead(q, new Set(["U"])).name, "U", "urgent is never snoozed")
	assert.equal(nextMustRead(q.slice(1), new Set(["A"])).name, "B")
	assert.equal(nextMustRead(q.slice(1), new Set(["A", "B"])), null)
	assert.equal(nextMustRead([], new Set()), null)
})

test("confirm says why it is waiting until the end is reached", () => {
	assert.deepEqual(confirmState({ reachedEnd: false, pending: false }), {
		ready: false,
		label: "Read to the end to confirm",
	})
	assert.deepEqual(confirmState({ reachedEnd: true, pending: false }), {
		ready: true,
		label: "I have read this",
	})
	assert.deepEqual(confirmState({ reachedEnd: true, pending: true }), {
		ready: false,
		label: "Recording…",
	})
})
