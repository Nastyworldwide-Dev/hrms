// alpha.7 §5.1 (A1) + alpha.8 (owner, iOS 26: "laggy when scrolling"). The
// large title is part of the page and scrolls away with it, as UIKit's large
// title does; nothing is animated per frame. When it has gone under the bar,
// a small centred title fades in. Told once by an IntersectionObserver, not
// by an ionScroll event on every frame, and nothing animates max-height (a
// layout property Safari recomputes on every frame).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const layout = read("../BaseLayout.vue")
const header = read("../glass/GAppHeader.vue")
const css = read("../../theme/glass-components.css")

test("the large title is page content and scrolls with it", () => {
	assert.match(layout, /<h1\s+v-if="pageTitle && isTabRoot"[^>]*class="g-large-title"/)
	assert.doesNotMatch(layout, /@ionScroll/)
	assert.match(layout, /new IntersectionObserver/)
	assert.match(layout, /provide\("gTitleCollapsed", collapsed\)/)
})

test("the bar shows the small title once the large one has gone", () => {
	assert.match(header, /inject\("gTitleCollapsed"/)
	assert.match(header, /'g-header--collapsed': collapsed/)
	assert.match(header, /class="g-header__mini"/)
})

test("nothing animates a layout property", () => {
	const root = postcss.parse(css)
	const offenders = []
	root.walkDecls(/^transition/, (d) => {
		if (/max-height|height\b(?!:)/.test(d.value) && /g-header|g-large-title/.test(d.parent.selector)) offenders.push(d.parent.selector)
	})
	assert.deepEqual(offenders, [])
})


// Owner, 25 Sep 2026: "there is a redundant title in the page and the top
// bar". Ionic keeps every tab page alive when you switch tabs; hiding a page
// made its large title "leave the screen", the observer said collapsed, and
// the page came back with BOTH the small bar title and the large one. The
// small title appears only when the large one scrolled UNDER THE BAR, i.e.
// it is above the scroll area's top edge, never because the page was hidden.
test("the small title shows only when the large one went up under the bar", () => {
	assert.match(layout, /entry\.boundingClientRect\.bottom\s*<=\s*entry\.rootBounds\.top/)
	assert.match(layout, /root:\s*await/)
})
