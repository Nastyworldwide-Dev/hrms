// FormField's error line carries the server's own words, and a server string with no spaces in it
// (a long id, a URL, a field path) cannot wrap at a space, so it ran off a 390px screen (design
// review of 3169ca158, 7 Oct 2026). `overflow-wrap: anywhere` lets it break wherever it must.
import assert from "node:assert"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

const CSS = fs.readFileSync(
	path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "glass-components.css"),
	"utf8"
)

// the rule that styles .g-field-error on its own (not the row-scoped override)
const block = CSS.match(/(?:^|\n)\.g-field-error\s*\{[^}]*\}/)?.[0] ?? ""

test("the field error rule is found", () => {
	assert.notEqual(block, "")
})

test("a long unbroken server string wraps instead of overflowing the screen", () => {
	assert.match(block, /overflow-wrap:\s*anywhere/)
})
