// alpha.14 K (27 Sep 2026 sweep): the empty lists said the same thing six
// ways — "No leave taken this year" (the list is not limited to a year),
// "Nothing here yet", "No shift requests yet"; bodies pointed at "New above",
// "tap New", or nothing. Apple ContentUnavailableView: the thing's own
// symbol, a title that states what is true, one line that says what to do,
// and the action itself when there is one.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const list = readFileSync(fileURLToPath(new URL("../ListView.vue", import.meta.url)), "utf8")
const table = list.slice(list.indexOf("const EMPTY_COPY = {"), list.indexOf("const emptyCopy"))
const titles = [...table.matchAll(/title: __\("([^"]+)"\)/g)].map((m) => m[1])
const bodies = [...table.matchAll(/body: __\("([^"]+)"\)/g)].map((m) => m[1])

test("every title is 'No <things> yet' — true, whatever the date range", () => {
	assert.ok(titles.length >= 9)
	for (const t of titles) assert.match(t, /^No [a-z -]+ yet$/, t)
})

test("every body is a short line saying what to do, and never points at a button", () => {
	for (const b of bodies) {
		assert.doesNotMatch(b, /New above|tap New|Use New/, b)
		assert.match(b, /^[A-Z].*\.$/, b)
		assert.ok(b.length <= 60, b)
	}
})

test("an empty list you can add to offers the action itself", () => {
	const tag = list.match(/<GEmptyState[\s\S]*?<\/GEmptyState>/)[0]
	assert.match(tag, /<template v-if="canCreate" #action>/)
	assert.match(tag, /<GButton[^>]*:label="__\('New', null, props\.doctype\)"/)
})
