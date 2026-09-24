// Owner ruling D3, 23 Sep 2026: Liquid Glass (backdrop blur + rim) belongs to
// CHROME only — the tab bar, the desktop side nav, the app header, sheets and
// toasts. Every content surface is solid. Apple HIG, Materials: "Don't use
// Liquid Glass in the content layer"; WWDC25: avoid glass on glass. A content
// panel that blurs puts a second glass layer under every sheet opened over it.
// This parses the stylesheet the way a browser does and fails on any rule that
// turns a blur on for something that is not chrome.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8")
const root = postcss.parse(css)

const CHROME = /g-tabbar|g-sidenav|g-header|g-sheet|g-modal|toast|g-scrim/

const blurring = []
root.walkDecls(/^(-webkit-)?backdrop-filter$/, (decl) => {
	if (decl.value.trim() === "none") return
	blurring.push(...decl.parent.selectors)
})

test("the stylesheet still blurs something (the parse found the chrome)", () => {
	assert.ok(blurring.some((s) => s.includes("g-tabbar")), "the tab bar must stay glass")
	assert.ok(blurring.some((s) => /g-sheet|g-modal/.test(s)), "sheets are chrome and are glass")
	assert.ok(blurring.some((s) => s.includes("toast")), "toasts are chrome and are glass")
})

test("only chrome blurs what is behind it (D3: content surfaces are solid)", () => {
	const content = [...new Set(blurring.filter((s) => !CHROME.test(s)))]
	assert.deepEqual(content, [], "content surfaces with a backdrop-filter")
})
