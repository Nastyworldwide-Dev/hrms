// "What the colours mean" (owner screenshot, 26 Sep 2026): the swatches
// stretched into bars across the row. The form row's "control fills the rest"
// rule matched them; a key swatch is a mark, excluded at the source, 29 pt like
// a row's icon well. Dot marks (travel, training, open, fix) draw as a dot in a
// plain tile, as the calendar draws them; open is a ring.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const css = read("../../../theme/glass-components.css")

test("the fill rule never stretches a key swatch", () => {
	assert.match(css, /\.g-form-row > :not\(\.g-form-row__label\):not\(\.g-form-row__switch\):not\(\.g-cal__swatch\) \{\s*flex: 1 1 0;/)
	assert.match(css, /\.g-form-row\.g-cal__key > \.g-cal__swatch \{\s*flex: 0 0 29px;\s*width: 29px;\s*height: 29px;/)
})

test("dot marks are keyed as dots, open as a ring", () => {
	const cal = read("../GCalendar.vue")
	assert.match(cal, /const DOT_KEYS = new Set\(\["travel", "training", "open", "needs_you"\]\)/)
	assert.match(css, /\.g-cal__swatch--mark\.g-cal__swatch--open::after \{\s*box-shadow: inset 0 0 0 1\.5px var\(--g-warn-ink\);/)
})
