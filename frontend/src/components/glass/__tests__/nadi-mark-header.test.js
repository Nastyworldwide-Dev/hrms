// Owner, 23 Sep: "the date on top nav is not good. It should be inside, not
// replacing Nadi. Use the Nadi logo we already use instead of the word."
// (alpha.4 P1-8, DETAIL §1.3). One mark, drawn in one place.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the Nadi mark is one component drawn from the brand tokens", () => {
	const mark = read("../GLogo.vue")
	assert.match(mark, /fill="var\(--g-brand\)"/)
	assert.match(mark, /fill="var\(--g-on-brand\)"/)
	assert.match(mark, /aria-label/)
})

test("the header shows the mark at the left of every tab page", () => {
	const header = read("../GAppHeader.vue")
	assert.match(header, /<GLogo v-if="!showBack"/)
	assert.doesNotMatch(header, /kicker/)
})

test("the side menu uses the same mark, not a second drawing", () => {
	const nav = read("../../SideNav.vue")
	assert.match(nav, /<GLogo/)
	assert.doesNotMatch(nav, /<rect width="32" height="32" rx="8"/)
})

test("Home's title is the brand, and the date is the first line of Today", () => {
	const home = read("../../../views/Home.vue")
	assert.doesNotMatch(home, /todayTitle/)
	const now = read("../../NowBar.vue")
	assert.match(now, /class="g-now__date"/)
	assert.match(now, /format\("dddd, D MMMM"\)/)
})
