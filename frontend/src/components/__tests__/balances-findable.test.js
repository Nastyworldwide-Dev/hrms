// Reported 25 Sep 2026: "where do I check my AL balance?" The balance was on
// Requests all along, as one unlabelled grey line under New request. It now
// reads as an iOS group: a "Leave left" header and one row that opens every
// balance, so nobody has to know the line is tappable.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../RequestBalances.vue", import.meta.url)), "utf8")

test("the balances have a header and a row that opens every balance", () => {
	assert.match(src, /__\("Leave left"\)/)
	assert.match(src, /:label="__\('All balances'\)"[\s\S]{0,40}@click="openAll"/)
})
