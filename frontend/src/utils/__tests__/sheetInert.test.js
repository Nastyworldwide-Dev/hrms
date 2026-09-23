// While a sheet is open, the page behind it must not take focus: two Tab
// presses used to walk out of the open day sheet into the page under the
// scrim (audit P0-4, WAI-ARIA dialog pattern). Sheets can stack, so the page
// stays inert until the LAST open sheet closes.
import { test } from "node:test"
import assert from "node:assert/strict"

import { holdPageInert, releasePageInert, _resetForTest } from "../sheetInert.js"

function fakePage() {
	return { inert: false }
}

test("an open sheet makes the page behind it inert, and closing it frees the page", () => {
	_resetForTest()
	const page = fakePage()
	holdPageInert(() => page)
	assert.equal(page.inert, true)
	releasePageInert(() => page)
	assert.equal(page.inert, false)
})

test("with two sheets open, the page stays inert until both close", () => {
	_resetForTest()
	const page = fakePage()
	holdPageInert(() => page)
	holdPageInert(() => page)
	releasePageInert(() => page)
	assert.equal(page.inert, true)
	releasePageInert(() => page)
	assert.equal(page.inert, false)
})

test("an extra release never leaves the count negative", () => {
	_resetForTest()
	const page = fakePage()
	releasePageInert(() => page)
	holdPageInert(() => page)
	assert.equal(page.inert, true)
	releasePageInert(() => page)
	assert.equal(page.inert, false)
})

test("no page mounted: nothing throws", () => {
	_resetForTest()
	holdPageInert(() => null)
	releasePageInert(() => null)
})
