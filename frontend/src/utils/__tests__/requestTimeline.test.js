import assert from "node:assert/strict"
import { test } from "node:test"

import { timelineLine } from "../requestTimeline.js"

// Owner, 13 Nov 2026: a claim says on what date its manager approved it.
test("the manager's approval of a claim is its own line", () => {
	const plain = (text, args = []) => args.reduce((s, a, i) => s.replace(`{${i}}`, a), text)
	assert.equal(
		timelineLine({ what: "manager_approved", who: "Azhar" }, plain),
		"Manager approved by Azhar"
	)
	assert.equal(timelineLine({ what: "manager_approved", who: null }, plain), "Manager approved")
})
