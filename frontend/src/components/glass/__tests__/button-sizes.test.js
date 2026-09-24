// alpha.6 B6: 8 different button heights were measured on one app (41, 44, 48,
// 50, 51, 52, 56, 61 px — alpha6-pages.md §F), because GButton's height was
// padding + line-height and so moved with every type change. Apple HIG
// Buttons: size shows importance by STYLE, not size; iOS 26 uses a capsule
// ("radius = half the height", WWDC25 356). One large height (48, on the 4pt grid;
// the current HIG publishes no fixed figure), one regular (44pt, the minimum
// target), both capsules.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)), "utf8")
const root = postcss.parse(css)
const decl = (selector, prop) => {
	let v
	root.walkRules((r) => {
		if (r.selectors.includes(selector)) r.walkDecls(prop, (d) => (v = d.value.trim()))
	})
	return v
}

test("the primary button has a fixed height, not padding + text", () => {
	assert.equal(decl(".g-btn", "height"), "48px")
	assert.match(decl(".g-btn", "padding"), /^0 /)
})

test("it is a capsule (radius = half the height)", () => {
	assert.equal(decl(".g-btn", "border-radius"), "24px")
})

test("the compact button is the 44px regular size, also a capsule", () => {
	assert.equal(decl(".g-btn--compact", "height"), "44px")
	assert.equal(decl(".g-btn--compact", "border-radius"), "22px")
})
