// Rows are 56px (owner ruling P5) — a list row is the app's main tap target
// and 44px is the platform FLOOR, not a design size.
//
// Except on Home. Home is one screen against a ~440px small-phone budget
// (home-fold-budget.test.js) and carries up to seven one-line rows; +12px
// each is up to 84px the fold was never measured for. Home keeps 44 through
// one modifier on its column until app-measure.mjs proves 56 fits.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const css = read("../../theme/glass-components.css").replace(/\/\*[\s\S]*?\*\//g, "")
const rule = (selector) => {
	const at = css.indexOf(`\n${selector} {`)
	assert.ok(at > -1, `${selector} rule exists`)
	return css.slice(at, css.indexOf("}", at))
}

test("a list row is 56px tall", () => {
	assert.match(rule(".g-row"), /min-height: 56px;/)
})

test("Home keeps 44px rows through one modifier on its column", () => {
	assert.match(rule(".g-rows--compact .g-row"), /min-height: 44px;/)
	assert.match(read("../../views/Home.vue"), /class="[^"]*\bg-rows--compact\b/)
})
