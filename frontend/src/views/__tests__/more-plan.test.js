// More holds what no tab owns, once (audit-pages §4, "Final More"):
// Help · Announcements · SOPs · Public holidays · Team (managers) · Apps.
// Leaves and Expenses are requests and live on Requests (PAGE-4); the "More"
// eyebrow repeated the title (PAGE-10); public holidays had no door except
// inside the Leaves dashboard (PAGE-20).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const more = read("../More.vue")
const nav = read("../../data/navItems.js")
const template = more.slice(0, more.indexOf("<script"))

test("Leaves and Expenses are not More rows (they are requests)", () => {
	assert.doesNotMatch(nav, /title: "Leaves"/)
	assert.doesNotMatch(nav, /title: "Expenses"/)
})

test("Help is called Help", () => {
	assert.match(nav, /title: "Help"/)
	assert.doesNotMatch(nav, /title: "Helpdesk"/)
})

test("public holidays have their own row, opening one list in a sheet", () => {
	assert.match(template, /__\(['"]Public holidays['"]\)/)
	assert.match(template, /<HolidayList/)
})

test("no eyebrow repeats the page title", () => {
	assert.doesNotMatch(template, /<span class="g-eyebrow">\{\{ __\("More"\) \}\}<\/span>/)
})

test("the holiday list waits for the employee before asking", () => {
	// Review of 40133f8f3: resource params are captured once; opening the sheet
	// before $employee resolved asked for nobody's holidays.
	assert.match(more, /<HolidayList v-if="holidaysOpen && employee\.data" \/>/)
})
