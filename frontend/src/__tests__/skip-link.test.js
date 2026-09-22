// A keyboard user walked the whole tab bar on every navigation
// (revamp slice A7, WCAG 2.2 SC 2.4.1 Bypass Blocks).
//
// Every screen puts the header controls and, on a tab destination, five tab
// buttons ahead of the content. Without a way past them, a keyboard or switch
// user pressed Tab through all of it again after every single route change.
//
// The target already existed: #main-content has been on the router outlet all
// along. Only the link to reach it was missing, which is why this is a small
// diff for a criterion the app failed outright.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const decomment = (text) =>
	text
		.split(/(<!--[\s\S]*?-->)/)
		.filter((part) => !part.startsWith("<!--"))
		.join("")
		.split(/(\/\*[\s\S]*?\*\/)/)
		.filter((part) => !part.startsWith("/*"))
		.join("")

test("the skip link is the first thing in the tab order", () => {
	// Placed before every other focusable element in App.vue. A skip link in
	// the middle of the shell skips nothing.
	const app = decomment(read("App.vue"))
	const link = app.indexOf('class="g-skip-link"')
	const banner = app.indexOf("<OfflineBanner")
	const outlet = app.indexOf("<ion-router-outlet")
	assert.ok(link > 0, "the link exists")
	assert.ok(link < banner && link < outlet, "and nothing focusable precedes it")
})

test("it points at a target that exists", () => {
	// An href to a missing id is a link that silently does nothing — and the
	// id is on the outlet, which is why this pins the pair rather than the link.
	const app = decomment(read("App.vue"))
	assert.match(app, /href="#main-content"/)
	assert.match(app, /<ion-router-outlet id="main-content"/)
})

test("it is hidden until focused, and never display:none", () => {
	// display:none removes an element from the tab order entirely, so a skip
	// link styled that way cannot be reached and is pure decoration. The
	// transform technique keeps it focusable.
	const css = decomment(read("theme/glass-components.css"))
	const block = css.slice(css.indexOf(".g-skip-link {"), css.indexOf(".g-skip-link:focus-visible"))
	assert.doesNotMatch(block, /display:\s*none/, "display:none is not focusable")
	assert.doesNotMatch(block, /visibility:\s*hidden/, "nor is visibility:hidden")
	assert.match(block, /transform:\s*translateY\(-200%\)/, "moved off-screen instead")
	const focused = css.slice(css.indexOf(".g-skip-link:focus-visible"))
	assert.match(focused, /transform:\s*translateY\(0\)/, "and back on focus")
})

test("its text is translated", () => {
	const app = decomment(read("App.vue"))
	assert.match(app, /__\("Skip to main content"\)/, "it is a sentence a person reads")
})
