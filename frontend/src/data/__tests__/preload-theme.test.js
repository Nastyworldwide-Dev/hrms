// data/theme.js runs only after main.js (a deferred module), so before it
// executes the page paints the light :root default from glass.css. A dark-mode
// user therefore flashed light on every load. index.html now carries an inline
// pre-paint script that resolves the stored preference synchronously, before
// first paint. If that script is ever removed or moved after <body>, the flash
// returns — so this pins its presence and position by reading the source.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const html = readFileSync(fileURLToPath(new URL("../../../index.html", import.meta.url)), "utf8")

test("index.html sets the theme before first paint", () => {
	// Uses the same storage key as data/theme.js — a drift here means the boot
	// theme and the runtime theme disagree.
	assert.match(html, /localStorage\.getItem\("hrms:theme"\)/)
	assert.match(html, /setAttribute\("data-theme"/)
})

test("the pre-paint script runs inside <head>, before <body>", () => {
	const theme = html.indexOf('localStorage.getItem("hrms:theme")')
	const headEnd = html.indexOf("</head>")
	const body = html.indexOf("<body")
	assert.ok(theme !== -1 && headEnd !== -1, "both markers must exist")
	assert.ok(theme < headEnd, "theme script must be inside <head>")
	assert.ok(theme < body, "theme script must run before <body> renders")
})
