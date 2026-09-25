// alpha.10 frame fixes (owner screenshots, 25 Sep 2026), each measured in WebKit:
// - the page followed the finger past its top and bottom: Ionic forces
//   overscroll on iOS per ion-content, so it is switched off for every page;
// - "Pull to refresh" showed beside the large title on a light overscroll;
// - the bell was a 44 pt circle beside a 34 pt avatar;
// - the tab icon touched the selected pill (0 pt above, 14 below the label).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("every page stops at its edges", async () => {
	assert.match(read("../../main.js"), /noOverscroll\(\)/)
	const { noOverscroll } = await import("../../utils/noOverscroll.js")
	const el = { tagName: "ION-CONTENT", nodeType: 1, forceOverscroll: undefined }
	globalThis.MutationObserver = class {
		observe() {}
	}
	noOverscroll({ addEventListener() {}, querySelectorAll: () => [el], documentElement: {} })
	assert.equal(el.forceOverscroll, false)
})

test("the refresh words wait for a real pull", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /ion-refresher\.refresher-pulling \.g-refresh,\s*ion-refresher\.refresher-cancelling \.g-refresh \{\s*display: none;/)
})

test("the avatar is the size of the bar buttons beside it", () => {
	assert.match(read("../glass/GAppHeader.vue"), /:size="44" round decorative/)
})

test("the tab has a definite height, so its content centres in the pill", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /ion-tab-button\.g-tabbar__btn \{[^}]*height: var\(--g-tabbar-height\);/)
})
