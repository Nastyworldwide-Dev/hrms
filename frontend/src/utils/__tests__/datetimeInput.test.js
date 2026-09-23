// GDateTimePicker hands the phone's own datetime wheel a value it can read and
// hands Frappe back the format it stores. The two formats differ by one
// character and the seconds, and a slip either way blanks the field.
import { test } from "node:test"
import assert from "node:assert/strict"

import { fromDatetimeLocal, toDateInput, toDatetimeLocal } from "../datetimeInput.js"

test("Frappe datetime -> datetime-local input", () => {
	assert.equal(toDatetimeLocal("2026-09-23 14:05:00"), "2026-09-23T14:05:00")
	assert.equal(toDatetimeLocal("2026-09-23 08:30:59.123456"), "2026-09-23T08:30:59")
	assert.equal(toDatetimeLocal("2026-09-23 08:30"), "2026-09-23T08:30:00")
})

test("datetime-local input -> Frappe datetime", () => {
	assert.equal(fromDatetimeLocal("2026-09-23T14:05"), "2026-09-23 14:05:00")
	assert.equal(fromDatetimeLocal("2026-09-23T14:05:07"), "2026-09-23 14:05:07")
})

test("round trip keeps the minute", () => {
	for (const v of ["2026-01-01 00:00:00", "2026-12-31 23:59:00", "2026-09-04 19:30:00"]) {
		assert.equal(fromDatetimeLocal(toDatetimeLocal(v)), v)
	}
	assert.equal(toDatetimeLocal(fromDatetimeLocal("2026-09-23T07:45")), "2026-09-23T07:45:00")
})

test("empty or unreadable values clear the field instead of throwing", () => {
	for (const v of ["", null, undefined, "not a date"]) {
		assert.equal(toDatetimeLocal(v), "")
		assert.equal(fromDatetimeLocal(v), "")
	}
})

test("date input takes the day only", () => {
	assert.equal(toDateInput("2026-09-23"), "2026-09-23")
	assert.equal(toDateInput("2026-09-23 00:00:00"), "2026-09-23")
	assert.equal(toDateInput(""), "")
	assert.equal(toDateInput(null), "")
})

test("a value with seconds survives an edit round trip (review of e61bf5e29)", () => {
	// The input carries seconds (step=1), so re-saving never zeroes them.
	assert.equal(toDatetimeLocal("2026-09-23 14:05:30"), "2026-09-23T14:05:30")
	assert.equal(fromDatetimeLocal(toDatetimeLocal("2026-09-23 14:05:30")), "2026-09-23 14:05:30")
})
