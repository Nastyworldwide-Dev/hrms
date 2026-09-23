// Desktop sheets are centred dialogs and dim the whole window, side nav
// included (audit F-5 / APP-14; HIG-SHEET, H4). Measured live 23 Sep at
// 1280x800 before the fix: sheet flush to the bottom (y=663), scrim from
// x=216 so the side nav stayed bright and clickable.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the scrim is never teleported above the sheet", () => {
	// Hotfix 23 Sep: teleported to <body>, the scrim painted over every sheet
	// and nothing inside one could be tapped (check in / out included).
	assert.doesNotMatch(read("../GModal.vue"), /<Teleport to="body"/)
})

test("the scrim sits beside the sheet in ion-app, outside the frozen page", () => {
	// alpha.4 P0-2/3, measured 23 Sep: rendered in place, the scrim lived
	// inside the page an open sheet makes inert, so a tap on the dim area
	// did nothing and only a pull-down closed the sheet. In ion-app it is a
	// sibling of ion-modal, in the same stacking context, below the sheet.
	// A Vue <Teleport> there lost its anchor when Ionic moved the modal, so the
	// scrim is placed by hand, right before the presented sheet.
	const modal = read("../GModal.vue")
	assert.doesNotMatch(modal, /<Teleport/)
	assert.match(modal, /function onWillPresent\(\) \{[^}]*mountScrim\(modal\.value\?\.\$el, closeOwnSheet\)/)
})

test("at lg the sheet is centred, not pinned to the bottom", () => {
	const css = read("../../../theme/glass-components.css")
	const lg = css.slice(css.indexOf("@media (min-width: 1024px) {\n\t.g-modal {"))
	assert.match(lg, /\.g-modal::part\(content\) \{[^}]*top: 50%[^}]*translate: 0 -50%/)
})
