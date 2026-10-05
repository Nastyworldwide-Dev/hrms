// Owner ruling 5 Oct 2026: a typed Overtime Pay claim is cut DOWN to the half hour. The form says so
// before the person types, or 1.37 saved as 1.0 reads as a bug.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { halfHourClaim, halfHourNote } from "../halfHourNote.js"

test("overtime pay says it is paid in half hours, with the example", () => {
	assert.equal(halfHourNote(false), "Paid in half hours: 1.37 is saved as 1.0, 1.6 as 1.5.")
})

test("replacement leave says nothing: it converts raw hours to days", () => {
	assert.equal(halfHourNote(true), "")
})

test("the note goes through translation", () => {
	assert.equal(halfHourNote(false, (t) => `[ms] ${t}`).startsWith("[ms] "), true)
})

test("the cut matches the server's rule (hrms.utils.ot_precision.half_hour_claim)", () => {
	for (const [typed, expected] of [[1.37, 1], [1.6, 1.5], [1.5, 1.5], [2, 2], [0.5, 0.5], [0.49, 0], [4.99, 4.5], [8.876944444, 8.5]]) {
		assert.equal(halfHourClaim(typed), expected, String(typed))
	}
})

test("nothing, zero, negative and junk are zero", () => {
	for (const v of [null, undefined, "", 0, -1, "abc", NaN, Infinity]) assert.equal(halfHourClaim(v), 0, String(v))
})

test("the OT form shows the note in the day footer for overtime pay only", () => {
	const form = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")
	assert.match(form, /import \{ halfHourNote \} from "\.\/halfHourNote\.js"/)
	assert.match(form, /halfHourNote\(isRL\.value, __\)/)
})
