// 6 Oct 2026: a phone that keeps Nadi in memory can run an old build for days,
// because the browser looks for a new sw.js only on a page load and about once
// a day. So the app ASKS (registration.update()) once at launch and again when
// the person comes back to it, at most once every 30 minutes. A found build
// still takes over only while the app is hidden (update-applies-quietly.test.js),
// and a failed check (offline) is one console line: no throw, no toast.
import { test, afterEach } from "node:test"
import assert from "node:assert/strict"

const MINUTE = 60 * 1000
const realNow = Date.now
const realWarn = console.warn
let loads = 0

afterEach(() => {
	Date.now = realNow
	console.warn = realWarn
})

async function stage({ update } = {}) {
	// import first: Vue looks at `document` when it loads, so the fake comes after
	const { setRegistration } = await import(`../swRegistration.js?check${(loads += 1)}`)
	const listeners = {}
	const sent = []
	let checks = 0
	let clock = 1_000_000
	Date.now = () => clock
	globalThis.document = {
		visibilityState: "visible",
		addEventListener: (type, fn) => (listeners[type] = fn),
	}
	const registration = {
		waiting: { postMessage: (message) => sent.push(message) },
		addEventListener() {},
		update: () => {
			checks += 1
			return update ? update() : Promise.resolve()
		},
	}
	return {
		setRegistration,
		registration,
		sent,
		listeners,
		checks: () => checks,
		advance: (ms) => (clock += ms),
		look(state) {
			globalThis.document.visibilityState = state
			listeners.visibilitychange()
		},
	}
}

test("the app asks for a new build once at launch", async () => {
	const app = await stage()
	app.setRegistration(app.registration)
	assert.equal(app.checks(), 1)
})

test("coming back to the app asks again once 30 minutes have passed", async () => {
	const app = await stage()
	app.setRegistration(app.registration)
	app.advance(10 * MINUTE)
	app.look("visible")
	assert.equal(app.checks(), 1, "10 minutes is too soon")
	app.advance(21 * MINUTE)
	app.look("visible")
	assert.equal(app.checks(), 2, "31 minutes since the last ask")
})

test("two returns inside 30 minutes ask only once", async () => {
	const app = await stage()
	app.setRegistration(app.registration)
	app.advance(31 * MINUTE)
	app.look("visible")
	app.advance(MINUTE)
	app.look("visible")
	assert.equal(app.checks(), 2, "launch + one return")
})

test("going out of sight never asks", async () => {
	const app = await stage()
	app.setRegistration(app.registration)
	app.advance(60 * MINUTE)
	app.look("hidden")
	assert.equal(app.checks(), 1)
})

test("a failed check is one console line and the hidden rule still holds", async () => {
	const lines = []
	console.warn = (...args) => lines.push(args)
	const app = await stage({ update: () => Promise.reject(new Error("offline")) })
	assert.doesNotThrow(() => app.setRegistration(app.registration))
	await new Promise((resolve) => setImmediate(resolve))
	assert.equal(lines.length, 1)
	assert.match(String(lines[0][0]), /^\[sw\]/)
	app.look("visible")
	assert.deepEqual(app.sent, [], "never while the person is looking at it")
	app.look("hidden")
	assert.deepEqual(app.sent, [{ type: "SKIP_WAITING" }])
})

test("a check that throws on the spot does not break the app either", async () => {
	console.warn = () => {}
	const app = await stage({
		update: () => {
			throw new Error("not allowed")
		},
	})
	assert.doesNotThrow(() => app.setRegistration(app.registration))
	app.advance(31 * MINUTE)
	assert.doesNotThrow(() => app.look("visible"))
	app.look("hidden")
	assert.deepEqual(app.sent, [{ type: "SKIP_WAITING" }])
})

test("a waiting build is let in only while the app is hidden", async () => {
	const app = await stage()
	app.setRegistration(app.registration)
	app.look("visible")
	assert.deepEqual(app.sent, [])
	app.look("hidden")
	assert.deepEqual(app.sent, [{ type: "SKIP_WAITING" }])
})
