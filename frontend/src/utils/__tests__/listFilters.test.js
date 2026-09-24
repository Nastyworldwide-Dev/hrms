// alpha.7 0.6: the Filters sheet asked people to pick "=", ">" or "<" beside
// every date. A filter row now says one thing, and the comparison follows
// from what the field means: "From" is on or after, "To" is on or before.
import { test } from "node:test"
import assert from "node:assert/strict"
import { filterCondition } from "../listFilters.js"

test("a start date keeps days on or after it", () => {
	for (const fieldname of ["from_date", "start_date"])
		assert.equal(filterCondition({ fieldname, fieldtype: "Date" }), ">=")
})

test("an end date keeps days on or before it", () => {
	for (const fieldname of ["to_date", "end_date"])
		assert.equal(filterCondition({ fieldname, fieldtype: "Date" }), "<=")
})

test("any other field, one date included, matches exactly", () => {
	assert.equal(filterCondition({ fieldname: "ot_date", fieldtype: "Date" }), "=")
	assert.equal(filterCondition({ fieldname: "posting_date", fieldtype: "Date" }), "=")
	assert.equal(filterCondition({ fieldname: "status", fieldtype: "Select" }), "=")
	assert.equal(filterCondition({ fieldname: "to_date_note", fieldtype: "Data" }), "=")
})
