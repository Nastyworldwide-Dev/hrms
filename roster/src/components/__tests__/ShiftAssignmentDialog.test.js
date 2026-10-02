// Desk Roster edit dialog (HR, 2 Oct 2026: "asal aku takleh update?").
// Shift Type, Shift Location and End Date were greyed out on an existing
// assignment and Update only woke for Status/End Date, so a shift could not
// be changed at all. Shift type/location now change the selected day through
// hrms.api.roster.change_shift_day (fenced, refuses a worked day).
//   node --test roster/src/components/__tests__/ShiftAssignmentDialog.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const view = readFileSync(fileURLToPath(new URL("../ShiftAssignmentDialog.vue", import.meta.url)), "utf8")

const field = (label) => {
	const i = view.indexOf(`label="${label}"`)
	return view.slice(view.lastIndexOf("<", i), view.indexOf("/>", i))
}

test("shift type, location and end date are editable on an existing shift", () => {
	for (const label of ["Shift Type", "Shift Location", "End Date"]) {
		assert.doesNotMatch(field(label), /:disabled="!!props\.shiftAssignmentName"/, label)
	}
})

test("start date and employee stay fixed", () => {
	assert.match(field("Start Date"), /:disabled="!!props\.shiftAssignmentName"/)
	assert.match(field("Employee"), /:disabled="!!props\.shiftAssignmentName"/)
})

test("a changed shift type wakes Update and goes to change_shift_day", () => {
	assert.match(view, /!shiftChanged\.value,/)
	assert.match(view, /if \(shiftChanged\.value\) changeShiftDay\.submit\(\)/)
	assert.match(view, /url: "hrms\.api\.roster\.change_shift_day"/)
})

// design review of f8d7da809: say the change is for one day, and never drop an
// end-date / status edit silently when the shift type changes too
test("shift type and location say they change this day only", () => {
	assert.match(field("Shift Type"), /:description="dayOnlyHint"/)
	assert.match(field("Shift Location"), /:description="dayOnlyHint"/)
	assert.match(view, /`Changes \$\{selectedDate\.value\} only`/)
})

test("a shift change plus an end-date or status change is refused, not half-applied", () => {
	assert.match(view, /shiftChanged\.value && \(form\.status !== doc\.status \|\| form\.end_date !== doc\.end_date\)/)
	assert.match(view, /one at a time/)
})
