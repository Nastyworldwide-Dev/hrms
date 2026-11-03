// The day sheet renders what utils/daySheet.js decides (01-calendar.md §4):
// the heading carries the day's status word, a waiting claim names its
// approver, and a future day's one action opens the leave form on that day.
// Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const sheet = readFileSync(fileURLToPath(new URL("../DaySheet.vue", import.meta.url)), "utf8")
const template = sheet.slice(0, sheet.indexOf("<script"))
const script = sheet.slice(sheet.indexOf("<script"))

test("the heading is the date plus the day's status word, on one line", () => {
	assert.match(sheet, /dayStatusWord\(/)
	assert.match(sheet, /format\("ddd D MMM"\)/, "short date so it stays one line")
	assert.match(sheet, /`\$\{date\} · \$\{__\(word\)\}`/)
})

test("the note is translated with its arguments (the approver's name)", () => {
	assert.match(sheet, /__\(action\.note, action\.noteArgs\)/)
})

test("a future day's action opens the leave form on that date", () => {
	assert.match(sheet, /action\.kind === 'leave'/)
	assert.match(sheet, /name: "LeaveApplicationFormView", query: \{ date: props\.date \}/)
})

test("the leave form starts on the day the sheet sent (?date=)", () => {
	const form = readFileSync(
		fileURLToPath(new URL("../../views/leave/Form.vue", import.meta.url)),
		"utf8"
	)
	assert.match(form, /dateFromRoute\(route\.query\)/)
	assert.match(form, /props\.id \? null : dateFromRoute/, "an existing request keeps its dates")
	assert.match(form, /from_date: startDay, to_date: startDay/)
})

// Owner, 3 Nov 2026: a coming Saturday, a holiday and a leave day said "You didn't
// check in this day."; the row now says what the day is (utils/daySheet.dayLine).
test("the no-taps row says what the day is, through dayLine", () => {
	assert.match(script, /import \{[^}]*\bdayLine\b[^}]*\} from "@\/utils\/daySheet"/)
	assert.match(template, /<GListRow :label="__\(noTapsLine\)" :tappable="false" wrap \/>/)
	assert.doesNotMatch(
		template,
		/__\('You didn\\'t check in this day\.'\)/,
		"no fixed wording left"
	)
})

test("the shift header steps aside on a day off", () => {
	assert.match(script, /if \(day\.off_kind\) return ""/)
})
