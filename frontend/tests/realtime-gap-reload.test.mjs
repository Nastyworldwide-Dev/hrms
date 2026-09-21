// A-C1 / A-H2 (21 Sep 2026): a socket reconnect replays nothing, and a tab
// hidden for minutes has a frozen socket. Registered reload hooks must run
// after the rooms are rejoined on a RECONNECT (not the first connect) and
// when the tab becomes visible after more than 60 s hidden.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/realtime-gap-reload.test.mjs
import test from "node:test"
import assert from "node:assert/strict"

import {
	onVisibilityChange,
	useListUpdate,
	useReloadOnGap,
} from "../src/composables/realtime.js"

function fakeSocket() {
	const handlers = {}
	const emitted = []
	return {
		emitted,
		emit: (...args) => emitted.push(args),
		on: (event, fn) => (handlers[event] = fn),
		off() {},
		fire: (event, data) => handlers[event]?.(data),
	}
}

test("the reload hook runs after rooms are rejoined on a reconnect, not on the first connect", () => {
	const socket = fakeSocket()
	const log = []
	useListUpdate(socket, "Leave Application", () => {})
	const detach = useReloadOnGap((why) => log.push([why, socket.emitted.length]))

	socket.fire("connect") // initial connect: nothing to catch up on
	assert.deepEqual(log, [])

	socket.fire("connect") // reconnect
	assert.equal(log.length, 1)
	assert.equal(log[0][0], "reconnect")
	assert.ok(
		log[0][1] >= 2,
		"the doctype_subscribe emits happened before the hook ran"
	)
	detach()
})

test("becoming visible after more than 60 s hidden reloads; a short hide does not", () => {
	const log = []
	const detach = useReloadOnGap((why) => log.push(why))
	const t0 = 1_000_000
	onVisibilityChange("hidden", t0)
	assert.equal(onVisibilityChange("visible", t0 + 30_000), false)
	assert.deepEqual(log, [])
	onVisibilityChange("hidden", t0)
	assert.equal(onVisibilityChange("visible", t0 + 61_000), true)
	assert.equal(log.length, 1)
	assert.match(log[0], /visible after 61 s hidden/)
	detach()
})

test("a detached hook no longer runs", () => {
	const log = []
	const detach = useReloadOnGap(() => log.push(1))
	detach()
	onVisibilityChange("hidden", 0)
	onVisibilityChange("visible", 120_000)
	assert.deepEqual(log, [])
})
