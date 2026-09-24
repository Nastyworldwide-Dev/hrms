// alpha.7 Phase 2 (plan §3, §10.3; owner + senior, 25 Sep): Home is
//   large title "Today" · Announcements FIRST, same place every day ·
//   the Today card (status + the one button, one solid card) · Needs you ·
//   Your week.
// The senior's goal is "make sure people read announcements": the section
// never moves and never vanishes; on a quiet day it is one line with See all.
// The check-in stays on the first screen, directly under it (§10.3).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const home = read("../Home.vue")
const tpl = home.slice(home.indexOf("<template>"), home.lastIndexOf("</template>"))
const ann = read("../../components/Announcements.vue")

test("Home's large title is Today", () => {
	assert.match(tpl, /<BaseLayout :pageTitle="__\('Today'\)">/)
})

test("the order: Announcements, the Today card, Needs you, Your week", () => {
	const order = ["<Announcements", 'class="g-today', "<NeedsYou", '__("Your week")']
	const at = order.map((m) => tpl.indexOf(m))
	for (const [i, m] of order.entries()) {
		assert.ok(at[i] > 0, `${m} is on Home`)
		if (i) assert.ok(at[i] > at[i - 1], `${m} comes after ${order[i - 1]}`)
	}
})

test("the status line and the button are ONE card", () => {
	const card = tpl.slice(tpl.indexOf('class="g-today'), tpl.indexOf("<NeedsYou"))
	assert.match(card, /<NowBar/)
	assert.match(card, /<CheckInPanel/)
})

test("a quiet day is one line with See all, in the same place", () => {
	assert.match(ann, /__\("No new announcements"\)/)
	assert.match(ann, /__\("See all"\)/)
	assert.doesNotMatch(ann, /__\("No news\."\)/)
})
