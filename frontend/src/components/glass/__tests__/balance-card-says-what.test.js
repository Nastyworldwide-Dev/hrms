// Family D (25 Sep 2026: "where do I check my AL balance?"): the Time off
// page's big number said "19" and nothing else on screen. A screen reader
// heard "19 days remaining of 20"; a sighted person saw a bare number. The
// card now says it: "days left of 20", under the number.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GBalanceCard.vue", import.meta.url)), "utf8")

test("the number says what it counts and of how many", () => {
	assert.match(src, /class="g-balance__unit"/)
	assert.match(src, /\{\{ unitLine \}\}/)
	assert.match(src, /"\{0\} left of \{1\}"/)
})
