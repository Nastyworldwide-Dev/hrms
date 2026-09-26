// alpha.12 K23: what the keyboard covers, read from the visual viewport.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { keyboardInset } from "../keyboardSafe.js"

test("an iPhone keyboard (874 tall page, 538 visible) covers 336 px", () => {
	assert.equal(keyboardInset(874, 538), 336)
})

test("browser chrome moving (under 80 px) is not a keyboard", () => {
	assert.equal(keyboardInset(874, 820), 0)
	assert.equal(keyboardInset(874, 874), 0)
})

test("a visual viewport scrolled down counts only what is below it", () => {
	assert.equal(keyboardInset(874, 538, 100), 236)
})

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Android resizes the page itself; iOS gets the helper; the Send bar lifts", () => {
	assert.match(read("../../../index.html"), /interactive-widget=resizes-content/)
	assert.match(read("../../main.js"), /keyboardSafe\(\)/)
	assert.match(read("../../theme/glass-components.css"), /var\(--g-keyboard-inset/)
})
