// A time slip is called one, everywhere the approver reads it (owner, 14 Oct 2026).
// Run: cd frontend && node --test src/utils/__tests__/requestKind.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { requestKind } from "../requestKind.js"

test("a fix a day sent as a time slip reads as a time slip", () => {
	assert.equal(requestKind("Attendance Request", { reason: "Time Slip" }), "Time slip")
})

test("any other fix a day, and other types, keep their word", () => {
	assert.equal(requestKind("Attendance Request", { reason: "On Duty" }), "Fix a day")
	assert.equal(requestKind("Leave Application", {}), "Time off")
	assert.equal(requestKind("Something Else"), "Something Else")
})
