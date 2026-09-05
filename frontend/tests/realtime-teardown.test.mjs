import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { useListUpdate } from "../src/composables/realtime.js"

function fakeSocket() {
	const handlers = []
	return {
		handlers,
		emit() {},
		on(event, fn) {
			handlers.push({ event, fn })
		},
		off(event, fn) {
			const i = handlers.findIndex((h) => h.event === event && h.fn === fn)
			if (i !== -1) handlers.splice(i, 1)
		},
		fire(event, data) {
			for (const h of [...handlers]) if (h.event === event) h.fn(data)
		},
	}
}

test("events for the doctype reach the callback; others do not", () => {
	const socket = fakeSocket()
	const seen = []
	useListUpdate(socket, "Leave Application", (name) => seen.push(name))
	socket.fire("list_update", { doctype: "Leave Application", name: "HR-LAP-1" })
	socket.fire("list_update", { doctype: "Expense Claim", name: "EXP-1" })
	assert.deepEqual(seen, ["HR-LAP-1"])
})

test("the returned detach removes exactly this handler, leaving siblings", () => {
	const socket = fakeSocket()
	const a = []
	const b = []
	const offA = useListUpdate(socket, "Shift Request", (n) => a.push(n))
	useListUpdate(socket, "Attendance Request", (n) => b.push(n))
	// Count only list_update handlers: subscribe() also wires one "connect"
	// handler per socket (wireReconnect, rejoins rooms after a mobile reconnect),
	// so raw handler count is list_update + 1 and isn't what this test is about.
	const listUpdateHandlers = () => socket.handlers.filter((h) => h.event === "list_update").length
	assert.equal(listUpdateHandlers(), 2)

	offA()
	assert.equal(listUpdateHandlers(), 1)
	socket.fire("list_update", { doctype: "Shift Request", name: "SR-1" })
	socket.fire("list_update", { doctype: "Attendance Request", name: "AR-1" })
	assert.deepEqual(a, [])
	assert.deepEqual(b, ["AR-1"])
})

test("re-registering after detach does not stack ghost handlers", () => {
	const socket = fakeSocket()
	const seen = []
	const off1 = useListUpdate(socket, "OT Request", (n) => seen.push(n))
	off1()
	useListUpdate(socket, "OT Request", (n) => seen.push(n))
	socket.fire("list_update", { doctype: "OT Request", name: "OT-1" })
	assert.deepEqual(seen, ["OT-1"])
})

test("a missing socket is a no-op, not a crash", () => {
	const off = useListUpdate(null, "Leave Application", () => {})
	assert.equal(typeof off, "function")
	off()
})

// Mutation pin: the behavioral tests above run outside a component, so they
// cannot see the auto-detach wiring. This line is what makes remounted
// components clean up — deleting it reverts the leak without failing a
// behavioral test, so it is pinned textually.
test("component-context auto-detach stays wired", () => {
	const source = readFileSync(
		fileURLToPath(new URL("../src/composables/realtime.js", import.meta.url)),
		"utf8"
	)
	assert.match(source, /if \(getCurrentInstance\(\)\) onBeforeUnmount\(off\)/)
})

// Adversarial review proved (by executing a real mount) that Vue unsets the
// component instance at an async hook's FIRST await — a useListUpdate call
// after it silently skips teardown registration and leaks. ListView is the
// caller that had exactly that shape, so its ordering is pinned.
test("ListView registers its listener before any await in onMounted", () => {
	const source = readFileSync(
		fileURLToPath(new URL("../src/components/ListView.vue", import.meta.url)),
		"utf8"
	)
	const mounted = source.slice(source.indexOf("onMounted(async"))
	const listUpdateAt = mounted.indexOf("useListUpdate(")
	const firstAwaitAt = mounted.indexOf("await ")
	assert.ok(
		listUpdateAt !== -1,
		"ListView must register a list_update listener"
	)
	assert.ok(firstAwaitAt !== -1, "expected the workflow await to still exist")
	assert.ok(
		listUpdateAt < firstAwaitAt,
		"useListUpdate must run BEFORE the first await — after it, " +
			"getCurrentInstance() is null and the unmount teardown never registers"
	)
})
