// alpha.14 (owner, 27 Sep 2026: "double title"). Found by the installed-iPhone
// journey (e2e/device-journey-audit.mjs): open a screen from a tab (the bell),
// come Back, and the tab shows the bar's small title AND the large one, on
// every tab. Ionic hides the tab page while the pushed screen is up; a hidden
// page reports zero-sized boxes, which the observer read as "the large title
// went above the top edge", and nothing corrected it on return.
// The rule: only a MEASURED page decides; a hidden page keeps what it was.
import { test } from "node:test"
import assert from "node:assert/strict"
import { titleCollapsed } from "../titleCollapse.js"

const box = (top, bottom) => ({ top, bottom, height: bottom - top })
const entry = (title, root, isIntersecting) => ({ boundingClientRect: title, rootBounds: root, isIntersecting })
const SCROLLER = box(65, 770)

test("the large title under the bar collapses the header", () => {
	assert.equal(titleCollapsed(entry(box(10, 51), SCROLLER, false), false), true)
})

test("the large title on screen shows it in full", () => {
	assert.equal(titleCollapsed(entry(box(67, 108), SCROLLER, true), true), false)
})

test("scrolled down past the bottom edge is not collapsed", () => {
	assert.equal(titleCollapsed(entry(box(900, 941), SCROLLER, false), false), false)
})

test("a hidden page (a pushed screen is up) keeps what it was", () => {
	const hidden = entry(box(0, 0), box(0, 0), false)
	assert.equal(titleCollapsed(hidden, false), false)
	assert.equal(titleCollapsed(hidden, true), true)
	assert.equal(titleCollapsed(entry(box(0, 0), null, false), false), false)
})
