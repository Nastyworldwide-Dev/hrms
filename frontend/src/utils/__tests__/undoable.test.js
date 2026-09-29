// Undo instead of "Are you sure?" (owner, 29 Sep 2026, alpha.21). Withdrawing
// a request asked "Withdraw this request? This cannot be undone." Now it goes
// at once with "Withdrawn · Undo", and the server is only asked after the undo
// window closes — so Undo never has anything to restore.
import assert from "node:assert/strict"
import { test } from "node:test"

import { undoable } from "../undoable.js"

function clock() {
	let now = 0
	const timers = []
	return {
		setTimeout: (fn, ms) => {
			const t = { fn, at: now + ms, done: false }
			timers.push(t)
			return t
		},
		clearTimeout: (t) => {
			if (t) t.done = true
		},
		advance(ms) {
			now += ms
			for (const t of timers) if (!t.done && t.at <= now) ((t.done = true), t.fn())
		},
	}
}

test("the action runs only after the window closes", () => {
	const c = clock()
	let ran = 0
	undoable(() => ran++, { ms: 5000, timers: c })
	c.advance(4999)
	assert.equal(ran, 0, "not before")
	c.advance(1)
	assert.equal(ran, 1, "once the window closes")
})

test("Undo inside the window means it never runs", () => {
	const c = clock()
	let ran = 0
	const pending = undoable(() => ran++, { ms: 5000, timers: c })
	c.advance(3000)
	pending.undo()
	c.advance(10000)
	assert.equal(ran, 0)
})

test("Undo after it ran does nothing and says so", () => {
	const c = clock()
	const pending = undoable(() => {}, { ms: 5000, timers: c })
	c.advance(5000)
	assert.equal(pending.undo(), false)
})

test("leaving the page runs it now, never loses it", () => {
	const c = clock()
	let ran = 0
	const pending = undoable(() => ran++, { ms: 5000, timers: c })
	pending.flush()
	assert.equal(ran, 1)
	c.advance(10000)
	assert.equal(ran, 1, "and not twice")
})
