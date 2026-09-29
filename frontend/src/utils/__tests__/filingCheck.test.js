// The person filing is told before Send (owner, 29 Sep 2026: guide everyone;
// alpha.21). The form asks the server's dry run when the dates or the kind of
// leave change, waits for the person to stop picking, and shows the answer
// under the dates. A stale answer (for dates since changed) is never shown.
import assert from "node:assert/strict"
import { test } from "node:test"

import { filingKey, readyToCheck } from "../filingCheck.js"

test("a leave is checked once it has a kind and both dates", () => {
	assert.equal(readyToCheck({ leave_type: "Annual", from_date: "2026-11-03", to_date: "2026-11-03" }), true)
	assert.equal(readyToCheck({ leave_type: "Annual", from_date: "2026-11-03" }), false)
	assert.equal(readyToCheck({ from_date: "2026-11-03", to_date: "2026-11-03" }), false)
	assert.equal(readyToCheck({ leave_type: "Annual", from_date: "2026-11-04", to_date: "2026-11-03" }), false, "end before start is the form's own error")
})

test("the answer belongs to the exact dates it was asked for", () => {
	const a = filingKey({ leave_type: "Annual", from_date: "2026-11-03", to_date: "2026-11-03", half_day: 0 })
	const b = filingKey({ leave_type: "Annual", from_date: "2026-11-03", to_date: "2026-11-04", half_day: 0 })
	const c = filingKey({ leave_type: "Annual", from_date: "2026-11-03", to_date: "2026-11-03", half_day: 1, half_day_session: "AM" })
	assert.notEqual(a, b)
	assert.notEqual(a, c, "a half day is a different question")
	assert.equal(a, filingKey({ from_date: "2026-11-03", leave_type: "Annual", to_date: "2026-11-03", half_day: 0 }))
})

test("the form wires it under the dates, announced", async () => {
	const { readFileSync } = await import("node:fs")
	const form = readFileSync(new URL("../../views/leave/Form.vue", import.meta.url), "utf8")
	assert.match(form, /url: "hrms\.api\.filing_check\.check_before_send"/)
	assert.match(form, /v-if="filingWarning && groupHasDates\(group\)"/)
	assert.match(form, /role="status"/)
})
