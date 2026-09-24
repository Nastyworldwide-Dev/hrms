// alpha.7 Phase 3 (plan §5.3; reviews A6, A11, A13): the iOS 26 inset-grouped
// list, measured on the owner's Settings screenshot (402 pt wide, 3x):
// group corner 26, gap between groups 35, row 54 with an icon tile / 44
// without, icon tile 29, row title 17 regular, separator starting at the text.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const tokens = JSON.parse(read("../../../../../design/tokens.json"))
const root = postcss.parse(read("../../../theme/glass-components.css"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("groups: 26 corner, 35 apart", () => {
	assert.equal(tokens.radius["radius-group"].value, "26px")
	assert.equal(tokens.layout["group-gap"].value, "35px")
	assert.equal(decls(".g-form-group")["border-radius"], "var(--g-radius-group)")
	assert.equal(decls(".g-list")["border-radius"], "var(--g-radius-group)")
})

test("rows: 17 pt title, 44 plain, 54 with an icon tile of 29", () => {
	assert.equal(tokens.layout["row-height-icon"].value, "54px")
	assert.equal(decls(".g-row__label")["font-size"], "17px")
	assert.equal(decls(".g-row")["min-height"], "var(--g-touch-target-min)")
	assert.equal(decls(".g-row:has(.g-row__well)")["min-height"], "var(--g-row-height-icon)")
	assert.equal(decls(".g-row__well").width, "29px")
})

test("the separator starts at the text, not the edge", () => {
	// 16 inset + 29 tile + 12 gap = 57 when there is a tile; 16 otherwise.
	assert.equal(decls(".g-row:has(.g-row__well) + .g-row::before").left, "57px")
	assert.equal(decls(".g-row + .g-row::before").right, "0")
})
