// alpha.7 §5.1 (A1): on a tab root the large title scrolls away with the page
// and a small centred title takes its place in the bar, as iOS does. Ionic's
// own scroll events drive it (ion-content scroll-events + ionScroll).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const layout = read("../BaseLayout.vue")
const header = read("../glass/GAppHeader.vue")

test("the tab root listens to its own scroll", () => {
	assert.match(layout, /<ion-content[^>]*:scroll-events="true"[^>]*@ionScroll="onScroll"/)
	assert.match(layout, /provide\("gTitleCollapsed", collapsed\)/)
})

test("the header shows the small title once the large one has gone", () => {
	assert.match(header, /inject\("gTitleCollapsed"/)
	assert.match(header, /'g-header--collapsed': collapsed/)
	assert.match(header, /class="g-header__mini"/)
})
