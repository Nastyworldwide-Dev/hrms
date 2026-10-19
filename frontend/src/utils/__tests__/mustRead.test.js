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
		canTick: false,
		label: "Read to the end to confirm",
	})
	assert.deepEqual(confirmState({ reachedEnd: true, pending: true, ticked: true }), {
		ready: false,
		canTick: true,
		label: "Recording…",
	})
})

// Review of alpha.38 L1 (6 Oct): when a notice's TEXT failed to load, the end marker
// was still on screen, so Confirm enabled and a person could record "I have read
// this" for a notice they never saw. Nothing to read means nothing to confirm.
test("a notice whose text did not load cannot be confirmed", () => {
	const s = confirmState({ reachedEnd: true, pending: false, failed: true })
	assert.equal(s.ready, false)
	assert.equal(s.label, "Load it to confirm")
})

test("a loaded notice read to the end can still be confirmed", () => {
	assert.equal(
		confirmState({ reachedEnd: true, pending: false, failed: false, ticked: true }).ready,
		true
	)
})

// Owner, 19 Oct 2026: "they must scroll to finish, and press tickbox to ensure they read". The
// tick is a statement the person makes; it can be made only once the end is reached, and the
// confirm waits for it.
test("the tickbox can be ticked only once the end is reached", () => {
	assert.equal(confirmState({ reachedEnd: false, pending: false }).canTick, false)
	assert.equal(confirmState({ reachedEnd: true, pending: false }).canTick, true)
	assert.equal(confirmState({ reachedEnd: true, pending: false, failed: true }).canTick, false)
})

test("read to the end but not ticked: confirm says to tick the box", () => {
	const s = confirmState({ reachedEnd: true, pending: false, ticked: false })
	assert.equal(s.ready, false)
	assert.equal(s.label, "Tick the box to confirm")
})

test("read to the end and ticked: confirm is ready", () => {
	assert.deepEqual(confirmState({ reachedEnd: true, pending: false, ticked: true }), {
		ready: true,
		canTick: true,
		label: "Confirm",
	})
})
