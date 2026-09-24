// alpha.6 B7 (owner screenshot, 24 Sep 2026): the New request sheet was five
// bare words — "No seperator, confusion, bad guidance design." Apple HIG Menus
// and Action sheets: related choices grouped with separators; each row an icon
// + title, and a one-line hint when the choice needs one. One icon per request
// kind, the same icon Notifications uses, so a kind looks the same everywhere.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const sheet = read("../GActionSheet.vue")
const requests = read("../../../views/Requests.vue")
const css = read("../../../theme/glass-components.css")

test("an action row can carry an icon and a hint", () => {
	assert.match(sheet, /<component[^>]*:is="action\.icon"/)
	assert.match(sheet, /action\.hint/)
})

test("the rows sit in one group with inset separators", () => {
	assert.match(sheet, /class="g-sheet__group"/)
	assert.match(css, /\.g-sheet__group \.g-sheet__action \+ \.g-sheet__action::before/)
})

test("every request type has an icon and a plain one-line hint", () => {
	const block = requests.slice(requests.indexOf("const requestTypes = ["), requests.indexOf("]", requests.indexOf("const requestTypes = [")))
	const rows = block.split(/\bkey:/).slice(1)
	assert.equal(rows.length, 5)
	for (const row of rows) {
		assert.match(row, /icon: \w+/, row)
		assert.match(row, /hint: __\("[^"]{8,60}"\)/, row)
	}
})
