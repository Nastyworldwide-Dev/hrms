// alpha.7 A16/B4: a duration is words, as iOS writes it: "Half day", "1 day",
// "1½ days", "3 days" — never "1d" or "0.5d".
import { test } from "node:test"
import assert from "node:assert/strict"
import { daysWords } from "../countWords.js"

test("whole days", () => {
	assert.equal(daysWords(1), "1 day")
	assert.equal(daysWords(3), "3 days")
	assert.equal(daysWords("2"), "2 days")
})

test("halves", () => {
	assert.equal(daysWords(0.5), "Half day")
	assert.equal(daysWords(1.5), "1½ days")
	assert.equal(daysWords(2.5), "2½ days")
})

test("nothing to say is empty, not 0 days", () => {
	assert.equal(daysWords(0), "")
	assert.equal(daysWords(null), "")
	assert.equal(daysWords(undefined), "")
})
