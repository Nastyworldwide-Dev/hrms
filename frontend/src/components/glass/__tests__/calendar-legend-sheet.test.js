// alpha.7 Phase 3 (plan §5.3, review A19): Apple's Calendar and Fitness keep
// the grid clean and explain the colours on request. The two lines of ten
// keys under the month move into a sheet opened by an info button; the keys
// still exist (colour is never the only signal: each day's name says it).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GCalendar.vue", import.meta.url)), "utf8")
const tpl = src.slice(src.indexOf("<template>"), src.indexOf("<script"))

test("the legend is behind an info button, in a sheet", () => {
	assert.match(tpl, /class="g-cal__info[^"]*"[\s\S]*@click="legendOpen = true"/)
	assert.match(tpl, /<GModal :is-open="legendOpen" :title="__\('What the colours mean'\)"/)
	assert.match(tpl, /<GModal[\s\S]*class="[^"]*g-cal__legend"/)
})

test("the grid no longer carries the legend inline", () => {
	const beforeSheet = tpl.slice(0, tpl.indexOf("<GModal"))
	assert.doesNotMatch(beforeSheet, /g-cal__legend/)
})
