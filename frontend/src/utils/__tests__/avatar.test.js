import assert from "node:assert/strict"
import { test } from "node:test"

import { initials } from "../avatar.js"

test("initials takes two letters from the given name, before bin/binti/a/l/a/p", () => {
	assert.equal(initials("Muhammad Hakim bin Ismail"), "MH")
	assert.equal(initials("Nurul Aina binti Rahman"), "NA")
	assert.equal(initials("Rajesh a/l Subramaniam"), "RS")
	assert.equal(initials("Kavitha a/p Muniandy"), "KM")
	assert.equal(initials("Lim Jia Hui"), "LJ")
})

test("initials copes with one word, blanks and lower case", () => {
	assert.equal(initials("Madonna"), "M")
	assert.equal(initials("  siti   aminah "), "SA")
	assert.equal(initials(""), "?")
	assert.equal(initials(undefined), "?")
})
