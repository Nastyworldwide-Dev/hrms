// alpha.14 F (owner screenshot, 27 Sep 2026: on You, the manager's name wrapped
// into three short right-aligned lines). iOS lays a value row out side by side
// only while label and value both fit on one line; otherwise the value goes
// UNDER the label, leading-aligned (UIListContentConfiguration.valueCell,
// prefersSideBySideTextAndSecondaryText). Widths from the spec, not the code.
import { test } from "node:test"
import assert from "node:assert/strict"
import { stacks } from "../valueRow.js"

// You page at 402: the row's inner width is 402 - 2*16 gutter - 2*16 pad = 338
const ROW = 338
const GAP = 12

test("a short value stays beside its label", () => {
	assert.equal(stacks({ label: 70, value: 120, row: ROW, gap: GAP }), false)
})

test("a value that would crowd the label goes under it", () => {
	// "Manager" 70 + a 290 pt name > 338
	assert.equal(stacks({ label: 70, value: 290, row: ROW, gap: GAP }), true)
})

test("exactly fitting stays side by side", () => {
	assert.equal(stacks({ label: 70, value: ROW - 70 - GAP, row: ROW, gap: GAP }), false)
})

test("an unmeasured row (hidden, 0 wide) is left as it is", () => {
	assert.equal(stacks({ label: 0, value: 0, row: 0, gap: GAP }), false)
})

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("every read-only label/value row in the app uses it", () => {
	assert.match(read("../../main.js"), /app\.directive\("value-row", vValueRow\)/)
	for (const file of ["../../views/Profile.vue", "../../components/LateCheckoutDialog.vue", "../../components/RemoteCheckinDialog.vue"]) {
		const src = read(file)
		const rows = src.match(/class="g-form-row g-form-row--readonly"/g) || []
		const directed = src.match(/v-value-row class="g-form-row g-form-row--readonly"/g) || []
		assert.equal(directed.length, rows.length, file)
	}
	assert.match(read("../../components/FormField.vue"), /v-value-row\s+class="g-form-row"/)
})
