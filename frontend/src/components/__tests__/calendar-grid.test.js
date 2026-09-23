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

test("D1: an absent day has its own look: a danger outline and danger ink", () => {
	const css = read("../../theme/glass-components.css")
	const rule = css.match(/\.g-cal__day--absent\s*\{[^}]*\}/)[0]
	assert.match(rule, /border-color:\s*var\(--g-danger-ink\)/)
	assert.match(rule, /color:\s*var\(--g-danger-ink\)/)
	// No tint: every danger tint under danger ink measured below 4.5:1 light.
	assert.doesNotMatch(rule, /background/)
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

test("D1: the absent legend key matches the day (an outline, not a fill)", () => {
	const css = read("../../theme/glass-components.css")
	const key = css.match(/\.g-cal__swatch--absent\s*\{[^}]*\}/)[0]
	assert.match(key, /inset 0 0 0 1\.5px var\(--g-danger-ink\)/)
	assert.match(key, /background:\s*transparent/)
})

test("D1: an absent TODAY keeps its danger outline (the today ring must not hide it)", () => {
	// Equal specificity: .g-cal__day--today came later in the file and took the
	// border, leaving colour alone to say "absent" on the one day it matters
	// most (WCAG 1.4.1; design review of 8f16f87ed).
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-cal__day--absent\.g-cal__day--today\s*\{[^}]*border-color:\s*var\(--g-danger-ink\)/)
})
