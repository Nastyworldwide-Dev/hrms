// Owner, 30 Sep 2026: "remove the new update popup, because we dont really
// need that". A new build must still reach people, and must still never
// reload the page under a half-written form. So it takes over only while the
// app is out of sight (the page is hidden), with no bar and no reload; the
// next screen they open is the new build. Stale chunks already reload
// themselves (router/stale-chunk.js).
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = (p) => fileURLToPath(new URL(`../../${p}`, import.meta.url))
const read = (p) => readFileSync(src(p), "utf8")

test("there is no update popup", () => {
	assert.equal(existsSync(src("components/UpdatePrompt.vue")), false)
	assert.doesNotMatch(read("App.vue"), /UpdatePrompt/)
	assert.doesNotMatch(read("theme/glass-components.css"), /\.g-update/)
})

function stage(visibility) {
	const listeners = {}
	const sent = []
	globalThis.document = {
		visibilityState: visibility,
		addEventListener: (type, fn) => (listeners[type] = fn),
	}
	const registration = {
		waiting: { postMessage: (message) => sent.push(message) },
		addEventListener() {},
	}
	return { listeners, sent, registration }
}

test("a waiting build is let in when the app goes out of sight", async () => {
	const { setRegistration } = await import(`../../data/swRegistration.js?${Date.now()}`)
	const { listeners, sent, registration } = stage("visible")
	setRegistration(registration)
	listeners.visibilitychange()
	assert.deepEqual(sent, [], "never while the person is looking at it")
	globalThis.document.visibilityState = "hidden"
	listeners.visibilitychange()
	assert.deepEqual(sent, [{ type: "SKIP_WAITING" }])
})

test("nothing reloads the page", () => {
	assert.doesNotMatch(read("data/swRegistration.js"), /location\.reload/)
})

test("the worker still waits to be asked", () => {
	const sw = read("../public/sw.js").replace(/\/\/[^\n]*/g, "")
	assert.doesNotMatch(sw, /^self\.skipWaiting\(\)/m)
	assert.match(sw, /"SKIP_WAITING"/)
})
