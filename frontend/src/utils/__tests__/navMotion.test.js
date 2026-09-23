// The right page transition per device (audit F-4 / APP-9, APP-10). The app
// forced the iPhone push on every device at 540 ms: Android and desktop got
// it too, and the desktop side nav slid on every section switch. The rules
// (plan 00-sheets-and-transitions.md §2; Apple HIG, Material 3 motion, NN/g
// animation duration):
//   reduced motion           -> none
//   a back that the browser or OS already animated (edge swipe) -> none
//   desktop (>= 1024px)      -> fade, 150 ms
//   iPhone / iPad            -> the iOS push (Ionic's own)
//   Android and the rest     -> fade-through, 200 ms
import { test } from "node:test"
import assert from "node:assert/strict"

import { pickNavMotion } from "../navMotion.js"

const base = { reducedMotion: false, width: 390, ios: false, direction: "forward", gesture: false }

test("reduced motion gets no animation", () => {
	assert.deepEqual(pickNavMotion({ ...base, reducedMotion: true }), { kind: "none" })
})

test("a gesture back gets no second animation, on any device", () => {
	assert.deepEqual(pickNavMotion({ ...base, ios: true, direction: "back", gesture: true }), {
		kind: "none",
	})
	assert.deepEqual(pickNavMotion({ ...base, direction: "back", gesture: true }), { kind: "none" })
})

test("desktop fades quickly", () => {
	assert.deepEqual(pickNavMotion({ ...base, width: 1280, ios: true }), {
		kind: "fade",
		duration: 150,
	})
})

test("iPhone keeps the iOS push", () => {
	assert.deepEqual(pickNavMotion({ ...base, ios: true }), { kind: "ios" })
})

test("Android fades through, well under half a second", () => {
	const motion = pickNavMotion(base)
	assert.deepEqual(motion, { kind: "fade", duration: 200 })
	assert.ok(motion.duration <= 500)
})

import { isBrowserTraversal, markBrowserTraversal } from "../browserTraversal.js"
import { queueBehindTraversal } from "../../router/traversalQueue.js"

test("a browser-driven Back stays flagged until the next in-app navigation", async () => {
	const listeners = []
	const after = []
	const router = {
		options: { history: { listen: (cb) => listeners.push(cb) } },
		afterEach: (fn) => after.push(fn),
		onError() {},
		push: () => Promise.resolve(),
		replace: () => Promise.resolve(),
		resolve: (to) => ({ fullPath: to }),
	}
	markBrowserTraversal(false)
	queueBehindTraversal(router)
	listeners.forEach((cb) => cb("/home", "/requests", { type: "pop", delta: -1 }))
	assert.equal(isBrowserTraversal(), true)
	after.forEach((fn) => fn({ fullPath: "/home" }, {}, undefined))
	await new Promise((resolve) => setTimeout(resolve, 5))
	assert.equal(isBrowserTraversal(), true, "Ionic may start the transition after the route lands")
	await router.push("/requests")
	assert.equal(isBrowserTraversal(), false)
})
