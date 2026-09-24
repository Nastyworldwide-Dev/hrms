// alpha.7 §5.7: the Home Screen icon shows the unread count (Badging API,
// iOS 16.4+ for Home Screen apps). The same number as the bell dot; 0 clears.
// Unsupported browsers do nothing and never throw.
import { test } from "node:test"
import assert from "node:assert/strict"
import { setBadge } from "../appBadge.js"

test("a count sets the badge; zero clears it", async () => {
	const calls = []
	const nav = { setAppBadge: (n) => calls.push(["set", n]), clearAppBadge: () => calls.push(["clear"]) }
	await setBadge(3, nav)
	await setBadge(0, nav)
	await setBadge(undefined, nav)
	assert.deepEqual(calls, [["set", 3], ["clear"], ["clear"]])
})

test("unsupported or refusing browsers are silent", async () => {
	await setBadge(2, {})
	await setBadge(2, { setAppBadge: () => Promise.reject(new Error("no")) })
})
