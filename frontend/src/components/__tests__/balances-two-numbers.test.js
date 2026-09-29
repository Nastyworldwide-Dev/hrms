// Leave balances as two big numbers, then All balances (owner, 29 Sep 2026,
// alpha.20 plan C: option A). The one line "Nadi W0 Annual 19 · All" read as a
// cramped sentence; the two most-used balances now read at a glance, each a
// number with its word under it, and every other type is one tap away.
// Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const src = read("../RequestBalances.vue")
const template = src.slice(0, src.indexOf("<script"))

test("the two pinned balances are numbers, each with its word", () => {
	assert.match(template, /v-for="row in shownLeave"/)
	assert.match(template, /class="g-balance-tile__number"[^>]*>\{\{ trim\(row\.balance\) \}\}/)
	assert.match(template, /class="g-balance-tile__label"[^>]*>\{\{ shortLeaveName\(row\.leave_type\) \}\}/)
})

test("All balances is a row under them, and opens the sheet", () => {
	const tiles = template.indexOf("g-balance-tile")
	const all = template.indexOf("__('All balances')")
	assert.ok(tiles > -1 && all > tiles, "All balances comes after the numbers")
	assert.match(template, /:label="__\('All balances'\)"[\s\S]{0,120}@click="openAll"/)
})

test("each tile is read as one sentence, not two stray numbers", () => {
	assert.match(template, /:aria-label="__\('\{0\}: \{1\} days left', \[shortLeaveName\(row\.leave_type\), trim\(row\.balance\)\]\)"/)
})

test("the tiles are Glass tokens, two across", () => {
	const css = read("../../theme/glass-components.css")
	const grid = css.match(/\.g-balance-tiles\s*\{[^}]*\}/)?.[0] || ""
	assert.match(grid, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/)
	const tile = css.match(/\.g-balance-tile\s*\{[^}]*\}/)?.[0] || ""
	assert.match(tile, /var\(--g-/, "tokens only")
	assert.doesNotMatch(tile, /#[0-9a-f]{3,6}/i, "no hard-coded colour")
})

test("a request's status stays on one line in the list", () => {
	const css = read("../../theme/glass-components.css")
	const rule = css.match(/\.g-form-row\.g-req-row > \.g-badge\s*\{[^}]*\}/)?.[0] || ""
	assert.match(rule, /white-space: nowrap/)
})

test("New request is on the trailing side of the title bar", () => {
	const header = read("../glass/GAppHeader.vue")
	assert.match(header, /<span v-if="\$slots\.primary" class="g-header__primary"><slot name="primary" \/><\/span>/)
	const css = read("../../theme/glass-components.css")
	assert.match(css.match(/\.g-header__primary\s*\{[^}]*\}/)?.[0] || "", /margin-left: auto/)
})

test("a single balance spans the row instead of leaving half of it empty", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-balance-tile:only-child\s*\{\s*grid-column: 1 \/ -1;/)
})
