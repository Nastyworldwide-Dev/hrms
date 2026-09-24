// Owner, 24 Sep 2026: the Time off page could be dragged sideways on iPhone
// ("some page are able to go horizontal like it doesnt stick").
//
// Cause (WebKit, not reproducible in Chromium or desktop devtools): iOS Safari
// draws a native date / time / datetime-local input as inline-flex, sizes it
// from its own formatted content, and ignores `width: 100%` while the control
// keeps its native appearance. The field grows past the column and the page
// gains a sideways scroll. Fix per the CSS spec's appearance rule: a control
// with `appearance: none` hands sizing back to the stylesheet; `min-width: 0`
// stops the flex default (min-width: auto) from re-growing it. Sources:
// gomakethings.com/articles/fixing-temporal-input-styling-in-safari,
// github.com/twbs/bootstrap/issues/34433.
//
// One rule for every temporal input, wherever it renders, so a new one cannot
// bring the drag back.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8")
const root = postcss.parse(css)

const TYPES = ["date", "time", "datetime-local", "month"]

function declsFor(type) {
	const found = {}
	root.walkRules((rule) => {
		if (!rule.selectors.some((s) => s.replace(/\s/g, "") === `input[type="${type}"]`)) return
		rule.walkDecls((d) => {
			found[d.prop] = d.value.trim()
		})
	})
	return found
}

for (const type of TYPES) {
	test(`input[type="${type}"] cannot grow past its column on iOS Safari`, () => {
		const d = declsFor(type)
		assert.equal(d["-webkit-appearance"], "none", "WebKit ignores width while the native appearance is kept")
		assert.equal(d.appearance, "none")
		assert.equal(d["min-width"], "0", "flex children default to min-width: auto and re-grow")
		assert.equal(d["max-width"], "100%")
	})
}
