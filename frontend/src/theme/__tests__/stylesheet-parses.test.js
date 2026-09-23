// The browser, not the source, decides which rules exist. On 23 Sep a comment
// in glass-components.css contained "pad-*/" — the "*/" ended the comment
// early, the rest of it became part of the next selector, and the browser
// dropped the tab-bar reservation rule. Content sat under the bar on every tab
// page while tabbar-reservation.test.mjs (which reads the source text) passed.
// This parses the stylesheet the way a browser does and checks the result.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(
	fileURLToPath(new URL("../glass-components.css", import.meta.url)),
	"utf8"
)
const root = postcss.parse(css)

const selectors = []
root.walkRules((rule) => selectors.push(...rule.selectors))

test("no selector carries comment text (a comment closed early)", () => {
	const broken = selectors.filter((s) =>
		/\*\/|\/\*|[a-z]{3,} [a-z]{3,} [a-z]{3,} [a-z]{3,} [a-z]{3,}/i.test(s)
	)
	assert.deepEqual(broken, [], "selectors that swallowed a comment")
})

test("the tab-bar reservation reaches the browser as a whole, valid rule", () => {
	// A browser drops the ENTIRE rule when any selector in its list is invalid,
	// so the rule must be exactly these two selectors and nothing else.
	const rules = []
	root.walkRules((rule) => {
		if (rule.selectors.includes("ion-tabs .g-page ion-content.ion-no-padding")) rules.push(rule)
	})
	assert.ok(rules.length > 0, "the reservation rule must exist")
	for (const rule of rules) {
		assert.deepEqual(rule.selectors, [
			"ion-tabs .g-page ion-content",
			"ion-tabs .g-page ion-content.ion-no-padding",
		])
	}
})

test("the sheet, now focused when it opens, uses the app's focus ring, not the browser's", () => {
	// GModal focuses .g-sheet (tabindex -1) on present so focus moves into the
	// dialog (fedb09a20). Every other focus target in this file pairs
	// outline:none with --g-shadow-focus-ring; the sheet had no rule, so a
	// keyboard-opened sheet drew the raw browser outline (design review).
	const decls = (selector) => {
		const out = {}
		root.walkRules((rule) => {
			if (rule.selectors.includes(selector)) rule.walkDecls((d) => (out[d.prop] = d.value))
		})
		return out
	}
	assert.equal(decls(".g-sheet:focus-visible").outline, "none")
	assert.match(decls(".g-sheet:focus-visible")["box-shadow"] || "", /--g-shadow-focus-ring-inset/)
	assert.equal(decls(".g-sheet:focus:not(:focus-visible)").outline, "none")
})

test("no grid column refuses to shrink below its content (reflow at 320px / 200% text)", () => {
	// `1fr` is `minmax(auto, 1fr)`: a column never narrower than its widest
	// content. At 320px with text at 200% the calendar's weekday row and the
	// balance cells pushed the page sideways and cut numbers in half (audit
	// P0-13, WCAG 1.4.10). minmax(0, 1fr) lets the column shrink; the content
	// wraps or scales instead.
	const bad = []
	root.walkDecls("grid-template-columns", (d) => {
		if (/repeat\([^,]+,\s*1fr\)/.test(d.value)) bad.push(`${d.parent.selector}: ${d.value}`)
	})
	assert.deepEqual(bad, [])
})
