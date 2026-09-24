// alpha.7 Phase 1 (plan §5.2, reviews A2/A7): iOS 26 draws content as FLAT
// cells on a grouped background. Measured on the owner's Settings screenshot:
// page #000 / cell #1C1C1E in dark; iOS light is #F2F2F7 / #FFFFFF (UIKit
// systemGroupedBackground / secondarySystemGroupedBackground). Nadi drew
// panels with a rim, an inner highlight, a drop shadow and a diagonal gloss.
// Glass (blur) stays on chrome only (D3); content has no decoration at all.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const tokens = JSON.parse(read("../../../../design/tokens.json"))
const themed = (name) => tokens["color-themed"][name].value

test("the page and the cell are iOS's grouped colours", () => {
	assert.deepEqual(themed("bg"), { light: "#F2F2F7", dark: "#000000" })
	assert.deepEqual(themed("glass-fill-fallback"), { light: "#FFFFFF", dark: "#1C1C1E" })
})

test("a content panel is flat: no rim, no shadow, no gloss", () => {
	const root = postcss.parse(read("../glass-components.css"))
	const decls = {}
	let gloss = false
	root.walkRules((rule) => {
		if (rule.parent.type !== "root") return
		if (rule.selectors.includes(".g-glass")) rule.walkDecls((d) => (decls[d.prop] = d.value))
		if (rule.selectors.includes(".g-glass::after")) gloss = true
	})
	assert.equal(decls.background, "var(--g-glass-fill-fallback)")
	assert.ok(!decls.border || /none|0/.test(decls.border), `border: ${decls.border}`)
	assert.ok(!decls["box-shadow"] || decls["box-shadow"] === "none", `box-shadow: ${decls["box-shadow"]}`)
	assert.equal(gloss, false, "the diagonal gloss is gone")
})

test("the browser bar matches the page", () => {
	const html = read("../../../index.html")
	assert.match(html, /<meta name="theme-color" content="#F2F2F7"/)
	assert.match(html, /dark \? "#000000" : "#F2F2F7"/)
})
