// The approved Calendar plan, grid half (docs/glass/plan/pages/01-calendar.md).
// D1: absent days had no colour and looked like blank days.
// D6: today was not marked.
// C6 (legend) is pinned in utils/__tests__/calendarLegend.test.js.
// Source-asserted where the SFC is concerned (no compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("D1: an absent day has its own colour", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-cal__day--absent\s*\{[^}]*background:/)
})

test("D6: today is marked on the grid", () => {
	const cal = read("../AttendanceCalendar.vue")
	assert.match(cal, /today:/)
	assert.match(read("../glass/GCalendar.vue"), /g-cal__day--today/)
})

// The approved Calendar plan, page half: the page is the month and the one
// thing each day needs. Repeats are cut.
const page = read("../../views/attendance/Dashboard.vue")
const pageTemplate = page.slice(0, page.indexOf("<script"))
const calTemplate = read("../AttendanceCalendar.vue").split("<script")[0]

test("D7: no count strip under the grid (the grid already shows it)", () => {
	assert.doesNotMatch(calTemplate, /<GStatPanel/)
})

test("D8: no overtime card on Calendar (the claim list lives on Requests)", () => {
	assert.doesNotMatch(pageTemplate, /Overtime to claim/)
})

test("D9: no 'start a request' rows (Requests has New request; the day sheet fixes a day)", () => {
	assert.doesNotMatch(pageTemplate, /AttendanceRequestFormView|ShiftRequestFormView/)
})

test("the two quiet links stay: all check-ins, your shifts", () => {
	assert.match(pageTemplate, /EmployeeCheckinListView/)
	assert.match(pageTemplate, /ShiftAssignmentListView/)
})
