// D4, 7 Oct 2026: the Desk month view shows a Roster Day marker (O / R / PH) on a day with no shift.
// get_events now carries marker events {roster_day, date, day_type}; they must never be read as a shift
// (they have no start_date) and are drawn only on an empty cell.
//   node --test roster/src/components/__tests__/MonthViewTable.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const table = readFileSync(fileURLToPath(new URL("../MonthViewTable.vue", import.meta.url)), "utf8")

test("a marker event is skipped by the shift mapper, before handleShifts could read it", () => {
	const loop = table.slice(table.indexOf("const mapEventsToDates"), table.indexOf("const handleHoliday"))
	assert.match(loop, /if \("roster_day" in event\) continue;/)
	assert.ok(loop.indexOf('"roster_day" in event') < loop.indexOf("handleShifts(event"))
})

test("markers are collected by employee and date from the events the server sent", () => {
	assert.match(table, /\(markers\[employee\] \|\|= \{\}\)\[event\.date\] = event\.day_type/)
	assert.match(table, /dayMarkers\.value = markers;/)
})

test("an empty cell shows the marker's full word, styled like a shift's own Day Type", () => {
	// design review of d93c4ab49: a bare grey letter with a tooltip had no accessible name and
	// looked unlike the same Day Type on a shift (full word, font-semibold)
	const cell = table.slice(table.indexOf("<!-- Roster Day marker"), table.indexOf("<!-- Add Shift -->"))
	assert.match(cell, /!events\.data\?\.\[employee\.name\]\?\.\[day\.date\]/)
	assert.match(cell, /class="text-center font-semibold"/)
	assert.match(cell, /\{\{ dayMarkers\[employee\.name\]\[day\.date\] \}\}/)
	assert.doesNotMatch(cell, /text-gray-500|:title=|DAY_TYPE_MARKS/)
	assert.doesNotMatch(table, /const DAY_TYPE_MARKS/)
})
