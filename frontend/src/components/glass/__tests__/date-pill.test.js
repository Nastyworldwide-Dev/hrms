// alpha.7 Phase 3 (plan §5.4, review B15): iOS shows a date or time in a
// form row as a COMPACT PILL (UIDatePicker .compact): the value in a small
// grey capsule, trailing. The native input keeps the phone's own picker;
// only its look changes. The menu chevron is iOS's up/down glyph (B16).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const root = postcss.parse(read("../../../theme/glass-components.css"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("a date in a form row is a grey pill", () => {
	const pill = decls(".g-form-group .g-datefield input")
	assert.equal(pill.background, "var(--g-icon-bg)")
	assert.equal(pill["border-radius"], "8px")
	assert.equal(pill.color, "var(--g-ink)")
	assert.equal(pill.width, "auto")
})

test("menus use the up/down chevron", () => {
	assert.match(read("../GSelect.vue"), /<ChevronsUpDown class="g-select__chevron"/)
	assert.match(read("../../Link.vue"), /<ChevronsUpDown class="g-linkpick__chevron"/)
})

test("no pill before a date is chosen", () => {
	assert.match(read("../GDatePicker.vue"), /'g-datefield--empty': !modelValue/)
	assert.equal(decls(".g-form-group .g-datefield--empty input").background, "transparent")
})
