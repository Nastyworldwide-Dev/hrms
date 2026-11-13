// Owner, 13 Nov 2026: a long receipt (a phone screenshot of a map) filled the whole
// preview sheet. A long image opens cropped to its top, with a button to see it whole.
import assert from "node:assert/strict"
import { test } from "node:test"

import { isLongImage } from "../previewCrop.js"

test("a phone screenshot is long", () => {
	assert.equal(isLongImage(1080, 2204), true)
})

test("a photo of a receipt in portrait is not cropped", () => {
	assert.equal(isLongImage(1200, 1600), false)
})

test("a landscape image is not long", () => {
	assert.equal(isLongImage(1600, 900), false)
})

test("unknown size is not cropped", () => {
	assert.equal(isLongImage(0, 0), false)
	assert.equal(isLongImage(undefined, 500), false)
})
