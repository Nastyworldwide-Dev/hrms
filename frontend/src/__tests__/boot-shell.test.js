// alpha.12 C3 (measured 26 Sep 2026): every screen was blank white until the
// whole app had booted — about 10 s on a slow phone. Apple (loading): "Show
// something as soon as possible. If you make people wait for loading to
// complete before displaying anything, they can interpret the lack of content
// as a problem with your app." The shell lives in index.html so it paints
// before any script, in the phone's own light/dark, and Vue replaces it on
// mount (it sits inside #app).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const html = readFileSync(fileURLToPath(new URL("../../index.html", import.meta.url)), "utf8")
const app = html.slice(html.indexOf('<div id="app">'), html.indexOf("</div>", html.indexOf('<div id="app">') + 20) + 400)

test("#app holds a static shell that paints before any script", () => {
	assert.match(app, /class="boot-shell"/)
	assert.match(app, /boot-shell__row/)
	assert.match(html, /<style>[\s\S]*\.boot-shell\b[\s\S]*<\/style>/)
})

test("the shell follows the phone's light and dark, with the app's own grounds", () => {
	const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"))
	assert.match(css, /#F2F2F7/i)
	assert.match(css, /prefers-color-scheme:\s*dark[\s\S]*#000000/i)
})

test("the shell is hidden from assistive tech and holds still under Reduce Motion", () => {
	assert.match(app, /aria-hidden="true"/)
	const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"))
	assert.match(css, /prefers-reduced-motion:\s*reduce/)
})
