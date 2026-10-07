// Focus must leave a page before the next one lands, or the browser reports
// "Blocked aria-hidden on an element because its descendant retained focus" on every push.
// But a navigation that stays on the page (a query change, or Back redirected onto the page by
// sheetGuard.js) hides nothing, and the focus GModal just returned to the opener must survive.
import { test, beforeEach, afterEach } from "node:test"
import assert from "node:assert/strict"

import { releaseFocusOnLeave } from "../focusRelease.js"
import { samePage } from "../samePage.js"

const realDocument = globalThis.document
let blurred

beforeEach(() => {
	blurred = 0
	globalThis.document = { activeElement: { blur: () => blurred++ } }
})

afterEach(() => {
	if (realDocument === undefined) delete globalThis.document
	else globalThis.document = realDocument
})

function hookedRouter() {
	const guards = []
	releaseFocusOnLeave({ beforeEach: (fn) => guards.push(fn) })
	assert.equal(guards.length, 1, "one guard, registered on the router")
	return guards[0]
}

test("leaving for another page blurs the control that holds focus", () => {
	const guard = hookedRouter()
	assert.equal(guard({ path: "/support" }, { path: "/more" }), undefined)
	assert.equal(blurred, 1)
})

test("a navigation that stays on the page keeps focus where it is", () => {
	const guard = hookedRouter()
	guard({ path: "/more", fullPath: "/more" }, { path: "/more", fullPath: "/more" })
	guard({ path: "/more", fullPath: "/more?tab=2" }, { path: "/more", fullPath: "/more" })
	assert.equal(blurred, 0)
})

test("nothing focused, or a focus that cannot blur, is not an error", () => {
	const guard = hookedRouter()
	globalThis.document = { activeElement: null }
	assert.doesNotThrow(() => guard({ path: "/a" }, { path: "/b" }))
	globalThis.document = { activeElement: {} }
	assert.doesNotThrow(() => guard({ path: "/a" }, { path: "/b" }))
})

test("samePage compares the path, not the query or the hash", () => {
	assert.equal(samePage({ path: "/more" }, { path: "/more" }), true)
	assert.equal(
		samePage({ path: "/more", fullPath: "/more?a=1" }, { path: "/more", fullPath: "/more" }),
		true
	)
	assert.equal(samePage({ path: "/support" }, { path: "/more" }), false)
})
