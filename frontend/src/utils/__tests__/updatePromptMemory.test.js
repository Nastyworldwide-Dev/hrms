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

import { shouldOfferUpdate } from "../updatePromptMemory.js"

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
