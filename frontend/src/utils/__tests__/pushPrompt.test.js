// The nudge on announcements (owner, 19 Oct 2026): "nudge people who still not yet enable this
// notification". Shown on the board and on each notice to anyone whose phone CAN get pushes but
// does not yet; never to someone who already has them, nor where they cannot work at all.
// Unlike the one-time soft ask, a "not now" there does not silence it: the owner asked for it on
// each new announcement. A browser block is told how to undo it, not offered a button that
// cannot work.
import { test } from "node:test"
import assert from "node:assert/strict"

import { pushNudge } from "../pushPrompt.js"

const can = {
	relayConfigured: true,
	siteEnabled: true,
	alreadyEnabled: false,
	notificationSupported: true,
	browserPermission: "default",
}

test("a phone that can get notifications but has not turned them on is nudged with a button", () => {
	assert.equal(pushNudge(can), "ask")
})

test("someone who already has notifications is not nudged", () => {
	assert.equal(pushNudge({ ...can, alreadyEnabled: true }), null)
})

test("a browser that blocked notifications is told how to undo it", () => {
	assert.equal(pushNudge({ ...can, browserPermission: "denied" }), "blocked")
})

test("where notifications cannot work at all, nothing is said", () => {
	assert.equal(pushNudge({ ...can, relayConfigured: false }), null)
	assert.equal(pushNudge({ ...can, siteEnabled: false }), null)
	assert.equal(pushNudge({ ...can, notificationSupported: false }), null)
})
