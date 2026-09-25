// alpha.8 r3 (owner, 25 Sep 2026: "overflow scrolling to the top and
// bottom"). Every list page scrolled 28 px beyond its content, empty or not:
// ListView put a SECOND scroller (overflow-y: auto, h-full + mb-7) inside
// ion-content's own, so two nested areas fought over the same drag. One
// scroller now: ion-content's, with load-more reading its scroll event.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../ListView.vue", import.meta.url)), "utf8")
const tpl = src.slice(src.indexOf("<template>"), src.indexOf("<script"))

test("the list has one scroller: ion-content's", () => {
	assert.doesNotMatch(tpl, /overflow-y-auto/)
	assert.doesNotMatch(tpl, /\bmb-7\b[^"]*h-full|h-full[^"]*\bmb-7\b/)
	assert.match(tpl, /<ion-content[^>]*:scroll-events="true"[^>]*@ionScroll="handleScroll"/)
})

test("load-more reads ion-content's own scroll element", () => {
	assert.match(src, /getScrollElement\?\.\(\)/)
})
