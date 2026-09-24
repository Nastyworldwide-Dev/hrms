// "Home is broken top to bottom" (owner, 23 Sep): blocks vanished when they
// had nothing to say, leaving a screen that read as broken. Rule (NN/g empty
// states; Carbon): a block always renders and says why it is empty. Plan
// P1-1: "Nothing waiting on you." for approvers, "No news." for the board.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Needs you stays for approvers, saying nothing is waiting", () => {
	const src = read("../NeedsYou.vue")
	assert.match(src, /v-if="rows\.length \|\| isApprover\.data"/)
	assert.match(src, /__\("Nothing waiting on you\."\)/)
})

test("Announcements always shows, saying there is no news", () => {
	const src = read("../Announcements.vue")
	assert.match(src, /__\("No new announcements"\)/)
	assert.doesNotMatch(src, /v-else-if="cards\.length" class="w-full"/)
})
