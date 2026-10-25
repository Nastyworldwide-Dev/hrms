// The gate's axe run, 25 Oct 2026: every sheet and the must-read notice read
// as a bare "dialog" (aria-dialog-name, serious, 144 screens). Ionic 7.4 copies
// aria-label from ion-modal to its role=dialog wrapper ONCE, at first load, and
// then removes it from the host — a title that arrives later (the must-read's,
// any sheet whose title is computed) never reaches the dialog.
import { test } from "node:test"
import assert from "node:assert/strict"

import { nameSheet } from "../sheetName.js"

function fakeModal() {
	const attrs = {}
	const wrapper = {
		setAttribute: (k, v) => (attrs[k] = v),
		removeAttribute: (k) => delete attrs[k],
	}
	const root = { querySelector: (sel) => (sel === ".modal-wrapper" ? wrapper : null) }
	return { el: { shadowRoot: root }, attrs }
}

test("the dialog is named with the title as it is when the sheet opens", () => {
	const m = fakeModal()
	nameSheet(m.el, "Approve 3 requests")
	assert.equal(m.attrs["aria-label"], "Approve 3 requests")
	nameSheet(m.el, "Leave balance")
	assert.equal(m.attrs["aria-label"], "Leave balance", "a reused sheet takes its new title")
})

test("no title leaves no empty name behind", () => {
	const m = fakeModal()
	nameSheet(m.el, "Old")
	nameSheet(m.el, "")
	assert.equal("aria-label" in m.attrs, false)
})

test("a modal not yet drawn is skipped, not thrown on", () => {
	assert.doesNotThrow(() => nameSheet(null, "x"))
	assert.doesNotThrow(() => nameSheet({}, "x"))
	assert.doesNotThrow(() => nameSheet({ shadowRoot: { querySelector: () => null } }, "x"))
})
