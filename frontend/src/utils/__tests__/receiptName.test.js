// A receipt is shown by the name at the end of its file URL (alpha.60).
// Run: cd frontend && node --test src/utils/__tests__/receiptName.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { receiptName } from "../receiptName.js"

test("the name is the last part of the URL, decoded", () => {
	assert.equal(receiptName("/private/files/lunch_ab12cd.jpg"), "lunch_ab12cd.jpg")
	assert.equal(receiptName("/private/files/parking%20slip.pdf?fid=1"), "parking slip.pdf")
})

test("no URL is no name, and a stray % is shown as it is", () => {
	assert.equal(receiptName(""), "")
	assert.equal(receiptName(null), "")
	assert.equal(receiptName("/files/100%.png"), "100%.png")
})
