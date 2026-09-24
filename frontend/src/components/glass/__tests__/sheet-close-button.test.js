// Closing a sheet needed a pull-down (owner, 23 Sep). A sheet shows a visible
// Close at the top (NN/g bottom sheets: an explicit close; M3: a sheet can be
// dismissed without the drag gesture). One GModal, so every sheet gets it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const modal = read("../GModal.vue")

test("every sheet has a Close button with a name, that closes that sheet", () => {
	assert.match(
		modal,
		/<GIconButton\s+class="g-sheet__close"\s+:label="__\('Close'\)"\s+@click="closeOwnSheet"/
	)
})

test("a sheet with a title shows it beside the Close button", () => {
	assert.match(modal, /<div class="g-sheet__head">[\s\S]*g-sheet__close[\s\S]*g-sheet__title/)
})

// alpha.6 B8. Apple HIG Sheets (iOS): "Cancel/Close on the leading edge, Done
// on the trailing edge"; iOS 26 draws Close as the × symbol. It was on the
// trailing edge; the trailing slot is for a sheet's own confirm action.
test("Close is on the LEADING edge of the bar", () => {
	const css = read("../../../theme/glass-components.css")
	assert.match(css, /\.g-sheet__close \{[^}]*grid-column: 1/)
	assert.match(modal, /<slot name="confirm"/)
})
