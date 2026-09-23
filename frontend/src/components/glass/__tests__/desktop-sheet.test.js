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
	assert.doesNotMatch(read("../GModal.vue"), /<Teleport/)
	assert.match(read("../GModal.vue"), /<div v-if="showModalBackdrop" class="g-scrim"/)
})

test("at lg the sheet is centred, not pinned to the bottom", () => {
	const css = read("../../../theme/glass-components.css")
	const lg = css.slice(css.indexOf("@media (min-width: 1024px) {\n\t.g-modal {"))
	assert.match(lg, /\.g-modal::part\(content\) \{[^}]*top: 50%[^}]*translate: 0 -50%/)
})
