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
	const held = holdPageInert(() => page)
	assert.equal(page.inert, true)
	releasePageInert(held)
	assert.equal(page.inert, false)
})

test("with two sheets open, the page stays inert until both close", () => {
	_resetForTest()
	const page = fakePage()
	const a = holdPageInert(() => page)
	const b = holdPageInert(() => page)
	releasePageInert(a)
	assert.equal(page.inert, true)
	releasePageInert(b)
	assert.equal(page.inert, false)
})

test("an extra release never leaves the count negative", () => {
	_resetForTest()
	const page = fakePage()
	releasePageInert(page)
	const held = holdPageInert(() => page)
	assert.equal(page.inert, true)
	releasePageInert(held)
	assert.equal(page.inert, false)
})

test("no page mounted: nothing throws", () => {
	_resetForTest()
	releasePageInert(holdPageInert(() => null))
})

test("the page that was frozen is the page that is freed, even after the route changed", () => {
	// Back pressed while a sheet was still opening: the sheet froze Calendar,
	// the route moved to Home, then the sheet closed. Re-finding "the visible
	// page" at release freed Home (never frozen) and left Calendar inert —
	// untappable the next time anyone went back to it.
	_resetForTest()
	const calendar = fakePage()
	const home = fakePage()
	const held = holdPageInert(() => calendar)
	releasePageInert(held)
	assert.equal(calendar.inert, false)
	assert.equal(home.inert, false)
})
