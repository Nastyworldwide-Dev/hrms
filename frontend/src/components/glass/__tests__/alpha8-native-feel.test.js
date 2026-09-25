// alpha.8 round 2 (owner's iPhone after deploy, 25 Sep 2026).
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

// "the blue stuff around the toggle": frappe-ui's forms plugin paints a
// checked checkbox blue with `[type=checkbox]:checked` (0,2,0), which beat
// the switch's own rule (0,1,0). The switch now outranks it in every state.
test("no blue square behind the switch, checked or focused", () => {
	for (const sel of [".g-switch__input[type=\"checkbox\"]", ".g-switch__input[type=\"checkbox\"]:checked", ".g-switch__input[type=\"checkbox\"]:focus"]) {
		const d = decls(sel)
		assert.equal(d["background-color"], "transparent", sel)
		assert.equal(d["background-image"], "none", sel)
		assert.equal(d["box-shadow"], "none", sel)
	}
})

// "the icon kinda goes out of where it should be": the lens was inset 4 pt
// inside a 52 pt tab, leaving the icon and label pressed against its edges,
// and a press shrank ONLY the icon. The lens fills the tab's height; a press
// scales the whole tab, as one piece.
test("the lens holds its icon and label; a press scales the whole tab", () => {
	assert.equal(decls(".g-tabbar__lens").top, "var(--g-tabbar-pad-top)")
	assert.equal(decls(".g-tabbar__lens").bottom, "var(--g-tabbar-pad-bottom)")
	assert.match(decls("ion-tab-button.g-tabbar__btn:active").transform || "", /scale\(0\.96\)/)
	assert.equal(decls("ion-tab-button.g-tabbar__btn:active .g-tabbar__well").transform, undefined)
})

// "separator inconsistency": a separator was placed by the row ABOVE (past
// the tile if the previous row had one), so a group mixing rows with and
// without tiles drew lines that started in different places. UIKit aligns a
// separator with the text of its own row: now keyed on the row below.
test("a separator starts at the text of its own row", () => {
	assert.equal(decls(".g-row + .g-row:has(.g-row__well)::before").left, "58px")
	assert.equal(decls(".g-row:has(.g-row__well) + .g-row::before").left, undefined)
})

// "can still zoom freely, goes up and down more than it should": the app
// SHELL (header, tab bar) rubber-banded with the page because the document
// itself could scroll; only the page's own content scrolls now.
test("the app shell never bounces; only the page content scrolls", () => {
	const html = decls("html")
	assert.equal(html["overscroll-behavior"], "none")
	assert.equal(html.overflow, "hidden")
})

// "Expensproved, not paid yet" (Expense detail): the centred bar title and a
// long status word overlapped. The three bar tracks are equal on the sides so
// the title stays centred and truncates; the status truncates in its own track.
test("the bar title and a long status never overlap", () => {
	assert.match(decls(".g-header--inline")["grid-template-columns"], /minmax\(0, 1fr\) minmax\(0, max-content\) minmax\(0, 1fr\)/)
	const actions = decls(".g-header--inline .g-header__actions")
	assert.equal(actions["min-width"], "0")
	assert.equal(actions.overflow, "hidden")
})

// "2▪", "19▪" on sent requests: Safari draws its number spinner on a disabled
// number input. A read-only row shows only the number.
test("no number spinner on a read-only row", () => {
	const css = read("../../../theme/glass-components.css")
	assert.match(css, /\.g-form-row--readonly input\[type="number"\]::-webkit-inner-spin-button/)
	assert.match(decls('.g-form-row--readonly input[type="number"]')["-moz-appearance"] || "", /textfield/)
})
