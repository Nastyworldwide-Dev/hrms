// "1 leave request(s)" and "3 day(s)" read as a machine talking (audit P2-3,
// basis W-PLAIN). A count says one or many, in words.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { countOf } from "../countWords.js"

test("one is singular, anything else plural", () => {
	assert.equal(countOf(1, "day"), "1 day")
	assert.equal(countOf(3, "day"), "3 days")
	assert.equal(countOf(0, "day"), "0 days")
	assert.equal(countOf(0.5, "day"), "0.5 days")
	assert.equal(countOf(2, "check-in outside the area", "check-ins outside the area"), "2 check-ins outside the area")
})

test("no screen text says (s) any more", () => {
	for (const file of [
		"../../components/NeedsYou.vue",
		"../../components/ReplacementLeaveClaimItem.vue",
		"../../components/RequestBalances.vue",
		"../../views/helpdesk/TicketNew.vue",
		"../../views/ot/OTRequestForm.vue",
		"../../views/ot/claimEmptyReason.js",
	]) {
		const src = readFileSync(fileURLToPath(new URL(file, import.meta.url)), "utf8")
		const screen = src.split("\n").filter((l) => !/console\.|logger|^\s*\/\//.test(l))
		assert.equal(screen.filter((l) => /\w\(s\)|\(es\)/.test(l)).length, 0, file)
	}
})

test("Home uses the plural the server sends, not noun + s (\"attendance fixes\")", () => {
	const src = readFileSync(fileURLToPath(new URL("../../components/NeedsYou.vue", import.meta.url)), "utf8")
	assert.match(src, /countOf\(row\.count, row\.noun, row\.nouns\)/)
	assert.doesNotMatch(src, /\{1\}s to approve/)
})
