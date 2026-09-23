// A dismissal the app forgets is not a dismissal (reported 23 September 2026).
//
// "The new version is still popping every time." Dismissing the update bar
// flipped a ref in the component and nothing else — the waiting service worker
// stayed waiting, so the next load registered it, `onNeedRefresh` fired, and
// the bar came back. On every reload. Forever, until the employee gave in and
// tapped Reload, which is the opposite of offering them a choice.
//
// The memory is PER BUILD, not for a period. An update is a specific build: it
// stops mattering the moment a newer one lands, and a timed silence — the
// shape the install prompt correctly uses — would hide a genuinely urgent fix
// for thirty days.
import { test } from "node:test"
import assert from "node:assert/strict"

import { shouldOfferUpdate, waitingBuildId } from "../updatePromptMemory.js"

//: The shape vite-plugin-pwa hands `onRegisteredSW`. Only the part this code
//: reads is modelled — a fuller fake would be asserting on the mock.
const registration = (scriptURL, key = "waiting") => (scriptURL ? { [key]: { scriptURL } } : {})

test("a build is identified by its revision, not its URL", () => {
	// Workbox stamps the revision on every build and only on a build, which is
	// exactly what a per-build key needs. The origin and path are noise: an app
	// moved behind a different path is still the same build.
	assert.equal(
		waitingBuildId(registration("https://a.example/sw.js?__WB_REVISION__=abc123")),
		"abc123"
	)
	assert.equal(
		waitingBuildId(registration("https://b.example/other/sw.js?__WB_REVISION__=abc123")),
		"abc123",
		"the same build behind a different path is the same build"
	)
})

test("two builds do not share an id", () => {
	const first = waitingBuildId(registration("/sw.js?__WB_REVISION__=aaa"))
	const second = waitingBuildId(registration("/sw.js?__WB_REVISION__=bbb"))
	assert.notEqual(first, second, "or dismissing one would silence the next")
})

test("an installing worker counts, not only a waiting one", () => {
	// The offer can fire while the new worker is still installing. Reading only
	// `waiting` returned null there, and a null id means "offer it" — so the
	// dismissal could not be recorded and the bar returned on the next load.
	assert.equal(waitingBuildId(registration("/sw.js?__WB_REVISION__=ccc", "installing")), "ccc")
})

test("no revision falls back to the whole URL", () => {
	// A site serving a worker without the parameter still gets a stable key,
	// so the offer is dismissed once rather than on every load. Worse than a
	// revision, much better than nothing.
	assert.equal(waitingBuildId(registration("/sw.js")), "/sw.js")
})

test("nothing waiting has no id", () => {
	assert.equal(waitingBuildId(undefined), null)
	assert.equal(waitingBuildId(null), null)
	assert.equal(waitingBuildId({}), null)
	assert.equal(waitingBuildId(registration("")), null)
})

test("a build that was put away is not offered again", () => {
	// THE BUG. Before this, the answer here was always true.
	assert.equal(shouldOfferUpdate("abc123", "abc123"), false)
})

test("a NEWER build is offered even after a dismissal", () => {
	// The reason this is keyed on the build rather than on a clock. Putting
	// one version away must not hide the next, which may be the fix for
	// whatever made them dismiss the first.
	assert.equal(shouldOfferUpdate("bbb", "aaa"), true)
})

test("an unidentifiable build is offered", () => {
	// Failing closed here would strand somebody on a broken build with no way
	// forward, which is the worse half of the rule this component balances.
	assert.equal(shouldOfferUpdate(null, "aaa"), true)
	assert.equal(shouldOfferUpdate(null, null), true)
})

test("no dismissal means offer it", () => {
	assert.equal(shouldOfferUpdate("abc123", null), true)
	assert.equal(shouldOfferUpdate("abc123", ""), true)
})
