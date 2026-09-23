// Field labels read in sentence case, acronyms intact (owner review, alpha.5).
import { test } from "node:test"
import assert from "node:assert/strict"

import { sentenceCase } from "../sentenceCase.js"

test("Title Case doctype labels become sentence case", () => {
	assert.equal(sentenceCase("Leave Type"), "Leave type")
	assert.equal(sentenceCase("From Date"), "From date")
	assert.equal(sentenceCase("Half Day Date"), "Half day date")
})

test("acronyms keep their capitals wherever they sit", () => {
	assert.equal(sentenceCase("HR Approver"), "HR approver")
	assert.equal(sentenceCase("Employee ID"), "Employee ID")
	assert.equal(sentenceCase("OT Hours"), "OT hours")
	assert.equal(sentenceCase("IT Declaration"), "IT declaration")
})

test("already sentence-case, punctuation and names survive", () => {
	assert.equal(sentenceCase("Reason for leave"), "Reason for leave")
	assert.equal(sentenceCase("Approver's Name (Optional)"), "Approver's name (optional)")
	assert.equal(sentenceCase("iPhone Model"), "iPhone model")
})

test("empty and missing labels are empty, not a crash", () => {
	assert.equal(sentenceCase(""), "")
	assert.equal(sentenceCase(undefined), "")
	assert.equal(sentenceCase(null), "")
})
