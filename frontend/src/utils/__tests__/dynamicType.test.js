// alpha.56 (Apple HIG Typography, Dynamic Type): the app follows the iPhone's
// Settings > Display & Brightness > Text Size. CSS gives the root html the system
// body font (-apple-system-body), which is 17px at the default setting; the app is
// drawn on a 16px root, so the size is scaled by 16/17 and the default looks as
// before. Larger settings grow everything in proportion.
import { test } from "node:test"
import assert from "node:assert/strict"
import { rootSizeFor, dynamicType } from "../dynamicType.js"

test("the iPhone's default text size draws the app exactly as before", () => {
	assert.equal(rootSizeFor(17), 16)
})

test("larger and smaller system sizes scale the app in proportion", () => {
	assert.equal(rootSizeFor(23), 23 * (16 / 17))
	assert.equal(rootSizeFor(14), 14 * (16 / 17))
})

test("no system size (not an iPhone, or unreadable) leaves the root alone", () => {
	for (const px of [0, NaN, undefined, null]) assert.equal(rootSizeFor(px), null)
})

function fakeDocument(fontSize) {
	const style = {}
	return {
		style,
		doc: {
			documentElement: { style },
			defaultView: { getComputedStyle: () => ({ fontSize }) },
		},
	}
}

test("on an iPhone the root size is set from the system size", () => {
	const { doc, style } = fakeDocument("17px")
	dynamicType(doc, { supports: () => true })
	assert.equal(style.fontSize, "16px")
})

test("off an iPhone nothing is touched", () => {
	const { doc, style } = fakeDocument("13px")
	dynamicType(doc, { supports: () => false })
	assert.equal(style.fontSize, undefined)
})
