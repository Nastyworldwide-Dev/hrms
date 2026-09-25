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

test("the selected tab carries the tint", () => {
	assert.match(read("../BottomTabs.vue"), /--color-selected: var\(--g-accent-ink\)/)
})


// alpha.8 (owner, 25 Sep 2026: "not alive and misaligned"). Measured on the
// owner's iPhone: the lens filled its whole tab cell (306.7-377 pt), touching
// the next tab and 4 pt from the bar edge on one side, 5 on the other. The
// lens is now a pill INSET inside the cell (equal on every side) that SLIDES
// to the chosen tab with Apple's default spring, and a pressed tab dips.
test("the lens is an inset pill that slides, and the press is felt", () => {
	const lens = decls(".g-tabbar__lens")
	assert.equal(lens.position, "absolute")
	assert.match(lens.transition || "", /left var\(--g-motion-tab-lens-duration\)/)
	assert.match(read("../BottomTabs.vue"), /class="g-tabbar__lens"/)
	assert.match(read("../BottomTabs.vue"), /:style="lensStyle"/)
	// r2: the whole tab scales (alpha8-native-feel.test.js)
	const pressed = decls("ion-tab-button.g-tabbar__btn:active")
	assert.match(pressed.transform || "", /scale\(0\.96\)/)
	// the whole tab cell no longer paints the lens
	assert.ok(!decls("ion-tab-button.g-tabbar__btn.tab-selected").background)
})

test("reduced motion: the lens moves without sliding", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /@media \(prefers-reduced-motion: reduce\)\s*\{[^}]*\.g-tabbar__lens\s*\{[^}]*transition: none/)
})
