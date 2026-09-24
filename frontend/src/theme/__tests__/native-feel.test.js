// alpha.6 D2 (rulebook P1–P3): what stops a PWA feeling like a web page.
// - a long-press on a button, tab or row must not select its text or pop the
//   iOS "Copy / Look Up" callout (native controls never do);
// - a page must never pan sideways (L1), whatever its content;
// - pulling past the top/bottom must show the page's own colour, not white.
// Content text (a note, an address) stays selectable, as in iOS.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8")

test("controls and chrome do not select text or show the long-press callout", () => {
	const rule = css.slice(css.indexOf("/* Native feel (alpha.6 D2"))
	const afterComment = rule.slice(rule.indexOf("*/") + 2)
	const block = afterComment.slice(0, afterComment.indexOf("}"))
	for (const sel of ["button", '[role="button"]', ".g-row", "ion-tab-bar"]) assert.ok(block.includes(sel), sel)
	assert.match(block, /-webkit-user-select:\s*none/)
	assert.match(block, /-webkit-touch-callout:\s*none/)
})

test("no page can be dragged sideways", () => {
	assert.match(css, /html,\s*body\s*{[^}]*overflow-x:\s*hidden/s)
	assert.match(css, /overscroll-behavior-x:\s*none/)
})

test("the overscroll area is the page colour", () => {
	assert.match(css, /html,\s*body\s*{[^}]*background(-color)?:\s*var\(--g-bg\)/s)
})

// alpha.6 B5 / HIG Color: lime means "act". An in-flight status chip is not an
// action, so it is not painted in the action colour.
test("the progress chip is not the action colour", () => {
	const rule = css.slice(css.indexOf(".g-chip--progress {"), css.indexOf("}", css.indexOf(".g-chip--progress {")))
	assert.doesNotMatch(rule, /--g-brand|--g-accent-ink/)
})
