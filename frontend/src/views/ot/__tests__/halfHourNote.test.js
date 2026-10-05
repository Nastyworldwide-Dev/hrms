// Owner ruling 5 Oct 2026: a typed Overtime Pay claim is cut DOWN to the half hour. The form says so
// before the person types, or 1.37 saved as 1.0 reads as a bug.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import * as halfHourNoteModule from "../halfHourNote.js"
const { halfHourNote } = halfHourNoteModule

test("overtime pay says it is paid in half hours, with the example", () => {
	assert.equal(halfHourNote(false), "Paid in half hours: 1.37 is saved as 1.0, 1.6 as 1.5.")
})

test("replacement leave says nothing: it converts raw hours to days", () => {
	assert.equal(halfHourNote(true), "")
})

test("the note goes through translation", () => {
	assert.equal(halfHourNote(false, (t) => `[ms] ${t}`).startsWith("[ms] "), true)
})

test("there is ONE half-hour rule, on the server: no second copy in the app", () => {
	// a JS copy once disagreed with the Python Decimal rule on 1.4999999999 (review of 112adc0af)
	assert.equal(typeof halfHourNoteModule.halfHourClaim, "undefined")
})

test("the OT form shows the note in the day footer for overtime pay only", () => {
	const form = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")
	assert.match(form, /import \{ halfHourNote \} from "\.\/halfHourNote\.js"/)
	assert.match(form, /halfHourNote\(isRL\.value, __\)/)
})
