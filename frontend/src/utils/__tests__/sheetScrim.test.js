// The dim area behind a sheet must take the tap that closes it (alpha.4
// P0-2/3; NN/g bottom sheets, M3: tapping the scrim dismisses). Rendered in
// place it sat inside the page the sheet makes inert, so the tap did nothing;
// in <body> it covered the sheet itself. It goes right before the sheet, in
// the same parent, where the sheet's higher z-index keeps it on top.
import { test } from "node:test"
import assert from "node:assert/strict"

import { mountScrim } from "../sheetScrim.js"

function fakeSheet() {
	const placed = []
	const doc = {
		createElement: (tag) => {
			const el = { tag, className: "", attrs: {}, listeners: {}, removed: false }
			el.setAttribute = (k, v) => (el.attrs[k] = v)
			el.addEventListener = (k, fn) => (el.listeners[k] = fn)
			el.remove = () => (el.removed = true)
			return el
		},
	}
	return { ownerDocument: doc, before: (el) => placed.push(el), placed }
}

test("the scrim goes right before the sheet, hidden from assistive tech", () => {
	const sheet = fakeSheet()
	const scrim = mountScrim(sheet, () => {})
	assert.deepEqual(sheet.placed, [scrim])
	assert.equal(scrim.className, "g-scrim")
	assert.equal(scrim.attrs["aria-hidden"], "true")
})

test("tapping the scrim calls the close handler", () => {
	let closed = 0
	const scrim = mountScrim(fakeSheet(), () => closed++)
	scrim.listeners.click()
	assert.equal(closed, 1)
})

test("no sheet element, no scrim", () => {
	assert.equal(mountScrim(null, () => {}), null)
})
