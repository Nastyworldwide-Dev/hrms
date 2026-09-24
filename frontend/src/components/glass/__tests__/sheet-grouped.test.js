// alpha.7 Phase 3 (plan §5.4; reviews B21, B22): a form sheet in iOS is the
// grouped background with its groups a step lighter (dark: #1C1C1E sheet,
// #2C2C2E cells; light: #F2F2F7 sheet, #FFFFFF cells). Nadi's sheet was
// white glass with white groups in light (no separation) and the expense
// sheet boxed every input again inside its group.
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

test("the sheet is the grouped background; its groups the elevated cell", () => {
	assert.deepEqual(tokens["color-themed"]["sheet-bg"].value, { light: "#F2F2F7", dark: "#1C1C1E" })
	assert.deepEqual(tokens["color-themed"]["sheet-cell"].value, { light: "#FFFFFF", dark: "#2C2C2E" })
	assert.equal(decls(".g-modal")["--background"], "var(--g-sheet-bg)")
	assert.equal(decls(".g-sheet .g-form-group")["background"], "var(--g-sheet-cell)")
	assert.equal(decls(".g-sheet__head").background, "var(--g-sheet-bg)")
})

test("the expense sheet does not box its inputs again", () => {
	assert.doesNotMatch(read("../../ExpensesTable.vue"), /\.expense-fields :deep\(input/)
})
