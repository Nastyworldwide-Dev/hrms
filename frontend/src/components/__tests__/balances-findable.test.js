// Reported 25 Sep 2026: "where do I check my AL balance?" The balance was on
// Requests all along, as one unlabelled grey line under New request. It now
// reads as an iOS group: a "Leave left" header and one row that opens every
// balance, so nobody has to know the line is tappable.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../RequestBalances.vue", import.meta.url)), "utf8")

test("the balances have a header and are one tappable row", () => {
	assert.match(src, /__\("Leave left"\)/)
	assert.match(src, /class="g-form-row g-form-row--action g-balances-row"[\s\S]{0,80}@click="openAll"/)
})
