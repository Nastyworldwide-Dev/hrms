// A blocked Send names the rows the person sees, in the words they see
// (UX review 21 Oct 2026, F2): "Leave Type, From Date, To Date fields are
// mandatory" named labels that are not on the screen.
// Run: cd frontend && node --test src/utils/__tests__/missingFields.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { isMissing, missingHint } from "../missingFields.js"

const __ = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => String(args[i]))
const LEAVE = [
	{ fieldname: "leave_type", label: "Leave Type", reqd: 1 },
	{ fieldname: "from_date", label: "From Date", reqd: 1 },
	{ fieldname: "to_date", label: "To Date", reqd: 1 },
	{ fieldname: "description", label: "Reason" },
]

test("an empty Time off names the rows as the screen shows them", () => {
	assert.equal(missingHint(LEAVE, {}, __), "Fill in Kind of leave, From, To.")
})

test("a filled form has no hint", () => {
	const model = { leave_type: "Casual Leave", from_date: "2026-10-21", to_date: "2026-10-21" }
	assert.equal(missingHint(LEAVE, model, __), "")
})

test("an empty required table counts as missing", () => {
	const f = { fieldname: "expenses", label: "Expenses", reqd: 1 }
	assert.equal(isMissing(f, { expenses: [] }), true)
	assert.equal(isMissing(f, { expenses: [{}] }), false)
})

test("hidden rows are never named", () => {
	const fields = [{ fieldname: "x", label: "X", reqd: 1, hidden: 1 }]
	assert.equal(missingHint(fields, {}, __), "")
})

test("a row the person cannot type in sends them to HR, not to the row", () => {
	const fields = [{ fieldname: "expense_approver", label: "Expense Approver", reqd: 1, read_only: 1 }]
	assert.equal(missingHint(fields, {}, __), "Something this form needs is not set up for you. Ask HR.")
})

test("the form's own read-only rule decides, so a write-denied row is not named (review)", () => {
	const fields = [{ fieldname: "leave_type", label: "Leave Type", reqd: 1 }]
	assert.match(missingHint(fields, {}, __, () => true), /Ask HR/)
})
