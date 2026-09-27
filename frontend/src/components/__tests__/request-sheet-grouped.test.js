// alpha.14 (owner screenshot, 27 Sep 2026): the request sheet — opened from
// Requests, Time off, the list pages and Approvals — drew a black page-coloured
// box inside the sheet, 12 pt grey labels in hand-made rows, the person's name
// cut at the right edge and the note as a field inside a row. It is now one
// group of the kit's rows on the sheet's own background, like every sheet.
// The on-screen check is e2e/sheet-consistency-audit.mjs (dark and light).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

for (const file of ["../RequestActionSheet.vue", "../ProfileInfoModal.vue"]) {
	test(`${file}: kit rows, no page-coloured box, no 12 pt labels`, () => {
		const tpl = read(file).split("<script")[0]
		assert.doesNotMatch(tpl, /\bbg-ground\b/)
		assert.doesNotMatch(tpl, /text-xs/)
		assert.match(tpl, /class="g-form-row g-form-row--readonly"/)
		assert.match(tpl, /v-value-row/)
	})
}

test("the request sheet's action bar is in the sheet's colour", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-request-sheet__bar \{[^}]*background: var\(--g-sheet-bg\);/)
})
