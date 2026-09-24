// alpha.7 Phase 1 (plan §5.1, review A5): the iOS 26 tab bar. A capsule
// (HIG: "capsules use a radius that's half the height"), ~61 pt tall and
// inset ~20 pt from the screen edges (measured on the owner's iPhone), with
// a lens pill behind the selected tab. Owner Q1: lime is the tint of the tab
// lens, so the selected icon and label take the accent ink.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const tokens = JSON.parse(read("../../../../design/tokens.json"))
const v = (g, k) => parseFloat(tokens[g][k].value)
const root = postcss.parse(read("../../theme/glass-components.css"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("the bar is a capsule about 61 pt tall", () => {
	const drawn =
		v("layout", "tabbar-height") + v("layout", "tabbar-pad-top") + v("layout", "tabbar-pad-bottom") + 2 * v("layout", "tabbar-border")
	assert.ok(drawn >= 58 && drawn <= 64, `drawn height ${drawn}`)
	assert.ok(v("radius", "radius-tabbar") >= drawn / 2, "a capsule: radius at least half the height")
})

test("the bar is inset 20 pt from the screen edges", () => {
	const bar = decls("ion-tab-bar.g-tabbar")
	assert.equal(bar.left, "var(--g-tabbar-inset)")
	assert.equal(bar.right, "var(--g-tabbar-inset)")
	assert.equal(v("layout", "tabbar-inset"), 20)
})

test("the selected tab sits in a lens and carries the tint", () => {
	const lens = decls("ion-tab-button.g-tabbar__btn.tab-selected")
	assert.ok(lens.background, "a lens fill behind the selected tab")
	assert.match(lens["border-radius"], /var\(--g-radius-tabbar\)|999|50%/)
	assert.match(read("../BottomTabs.vue"), /--color-selected: var\(--g-accent-ink\)/)
})
