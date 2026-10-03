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
	assert.match(view, /shiftChanged\.value &&\s*\(form\.status !== doc\.status \|\| \(form\.end_date \|\| null\) !== \(doc\.end_date \|\| null\)\)/)
	assert.match(view, /one at a time/)
})

// review of b4d308942: an open-ended shift's blank end date ("" vs null) is not a change
test("a blank end date matches an open-ended shift", () => {
	assert.match(view, /\(form\.end_date \|\| null\) === \(shiftAssignment\.value\?\.doc\?\.end_date \|\| null\)/)
})

// HR, 2 Oct 2026: Day Type on the roster sets the kind of day and its OT rate
const table = readFileSync(fileURLToPath(new URL("../MonthViewTable.vue", import.meta.url)), "utf8")

test("the dialog offers the five day types, None first", () => {
	assert.match(view, /label="Day Type"/)
	assert.match(view, /\["None", "Work Day", "Rest Day", "Off Day", "Public Holiday"\]/)
})

test("every save path sends the day type", () => {
	assert.equal(view.match(/day_type: form\.day_type \|\| "None"/g).length, 3)
})

test("a changed day type is a one-day change", () => {
	assert.match(view, /\(form\.day_type \|\| "None"\) !== \(shiftAssignment\.value\.doc\.day_type \|\| "None"\)/)
})

test("the month view shows a day type that is set", () => {
	assert.match(table, /day_type: event\.day_type/)
	assert.match(table, /shift\['day_type'\] !== 'None'/)
})

// Fahmie, 3 Oct 2026: "User ... does not have doctype access via role permission
// for document Shift Assignment". The Desk Roster deleted and updated through
// frappe.client set_value / delete, which asks Frappe for cancel and delete — a
// Shift Supervisor holds neither. Every roster write now goes through
// hrms.api.roster, where the roster fence decides. This pins the CLASS: no
// generic Frappe write resource anywhere in the roster app.
import { readdirSync } from "node:fs"
import { join } from "node:path"

const srcDir = fileURLToPath(new URL("../../", import.meta.url))
const sources = (dir) =>
	readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
		e.isDirectory()
			? e.name === "__tests__"
				? []
				: sources(join(dir, e.name))
			: /\.(vue|ts|js)$/.test(e.name)
				? [join(dir, e.name)]
				: []
	)

test("no roster screen writes through a generic Frappe resource", () => {
	for (const file of sources(srcDir)) {
		const text = readFileSync(file, "utf8")
		assert.doesNotMatch(text, /setValue\s*\.\s*submit|\.delete\s*\.\s*submit|\.insert\s*\.\s*submit/, file)
		assert.doesNotMatch(
			text,
			/frappe\.client\.(set_value|delete|insert|insert_many|submit|cancel|save|bulk_update|rename_doc)|frappe\.desk\.form\.save|\.setValue\.|\.update\s*\.\s*submit/,
			file
		)
	}
})

test("delete and update use the roster API", () => {
	assert.match(view, /url: "hrms\.api\.roster\.delete_shift_assignment"/)
	assert.match(view, /url: "hrms\.api\.roster\.update_shift_assignment"/)
})
