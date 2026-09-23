// Inter was downloaded twice on every page: frappe-ui's style.css registers a
// variable "InterVar" and 36 static "Inter" weights and italics, and the app's
// font stacks ask for "Inter" — so browsers fetched the static weights as
// well as the variable file (~770 kB per first visit, audit F-11 / APP-27).
// The app registers Inter once, from the one variable file, and does not
// import frappe-ui's font sheet.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("frappe-ui's font sheet is not imported", () => {
	const main = read("../../main.css")
	assert.doesNotMatch(main, /@import "frappe-ui\/src\/style\.css"/)
	assert.doesNotMatch(main, /fonts\/Inter\/inter\.css/)
})

test("Inter is registered once, from the variable file, normal style only", () => {
	const fonts = read("../fonts.css")
	const inter = [...fonts.matchAll(/@font-face\s*\{[^}]*font-family:\s*"Inter";[^}]*\}/g)]
	assert.equal(inter.length, 1)
	assert.match(inter[0][0], /Inter\.var\.woff2/)
	assert.match(inter[0][0], /font-weight:\s*100 900/)
})

test("Tailwind's layers still load (only the font sheet was dropped)", () => {
	const main = read("../../main.css")
	assert.match(main, /@tailwind base;/)
	assert.match(main, /@tailwind utilities;/)
})
