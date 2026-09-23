// "Worked" is one rule (owner bug, 23 Sep 2026): the Requests row names the
// day with no attendance, and a tap opens THAT day on the Calendar.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { unmarkedLabel, unmarkedRoute } from "../unmarkedLabel.js"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const same = (text, args = []) => text.replace(/\{(\d+)\}/g, (_, i) => args[i])

test("one day is named: weekday, day, month", () => {
	assert.equal(unmarkedLabel({ days: 1, dates: ["2026-09-16"] }, same), "Wed 16 Sep has no attendance")
})

test("several days: the count, then up to three dates", () => {
	assert.equal(
		unmarkedLabel({ days: 2, dates: ["2026-09-16", "2026-09-18"] }, same),
		"2 days have no attendance · 16, 18 Sep"
	)
	assert.equal(
		unmarkedLabel({ days: 4, dates: ["2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19"] }, same),
		"4 days have no attendance · 16, 17, 18 Sep…"
	)
})

test("dates across two months keep each month", () => {
	assert.equal(
		unmarkedLabel({ days: 2, dates: ["2026-08-30", "2026-09-02"] }, same),
		"2 days have no attendance · 30 Aug, 2 Sep"
	)
})

test("an older server with only a count still says something true", () => {
	assert.equal(unmarkedLabel({ days: 3 }, same), "3 days have no attendance")
})

test("a tap opens the Calendar on the first day", () => {
	assert.deepEqual(unmarkedRoute({ days: 2, dates: ["2026-09-16", "2026-09-18"] }), {
		name: "AttendanceDashboard",
		query: { date: "2026-09-16" },
	})
	assert.deepEqual(unmarkedRoute({ days: 3 }), { name: "AttendanceDashboard" })
})

test("the Requests row uses the helper and the Calendar opens ?date=", () => {
	const row = read("../../components/RequestBalances.vue")
	assert.match(row, /unmarkedLabel\(attendance, __\)/)
	assert.match(row, /router\.push\(unmarkedRoute\(attendance\)\)/)
	assert.doesNotMatch(row, /with no attendance — fix before payroll/)
	const cal = read("../../components/AttendanceCalendar.vue")
	assert.match(cal, /dateFromRoute\(route\.query\)/, "the Calendar reads ?date=")
})
