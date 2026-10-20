// Every state that dims "Add expense" says why (alpha.60; the #4855 class:
// list them all, in one place). The hint IS the disabled rule, so a dimmed
// button can never lack its reason.
// Run: cd frontend && node --test src/utils/__tests__/addItemHint.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { addItemHint } from "../addItemHint.js"

const __ = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => String(args[i]))
const FIELDS = [
	{ fieldname: "expense_date", label: "Date", reqd: 1 },
	{ fieldname: "expense_type", label: "Expense Claim Type", reqd: 1 },
	{ fieldname: "description", label: "Description" },
	{ fieldname: "amount", label: "Amount (MYR)", reqd: 1 },
]
const full = {
	expense_date: "2026-10-20",
	expense_type: "Parking",
	amount: 12,
	receipt: "/private/files/a.jpg",
}
const hint = (item, o = {}) =>
	addItemHint(
		{ fields: FIELDS, item, needsReceipt: true, uploading: false, loadFailed: false, ...o },
		__
	)

test("a complete line has no reason and Add is live", () => {
	assert.equal(hint(full), "")
})

test("the form that failed to load says so", () => {
	assert.equal(hint(full, { loadFailed: true }), "This form could not be loaded. Try again.")
})

test("the first empty required field is named by the row's own word", () => {
	assert.equal(hint({ ...full, expense_type: "" }), "Fill in Type.")
	assert.equal(hint({ ...full, amount: 0 }), "Fill in Amount (MYR).")
})

test("an upload in flight, then a missing receipt", () => {
	assert.equal(hint(full, { uploading: true }), "Wait for the file to finish uploading.")
	assert.equal(hint({ ...full, receipt: "" }), "Add the receipt for this item.")
	assert.equal(hint({ ...full, receipt: "" }, { needsReceipt: false }), "")
})

test("a mileage line names the distance, not the amount it works out", () => {
	// review of 5b8da3417: the amount is read-only and filled from the km, so
	// "Fill in Amount" pointed at a field nobody can type in
	const shown = [
		{ fieldname: "expense_type", label: "Expense Claim Type", reqd: 1 },
		{ fieldname: "distance_km", label: "Distance (km)", reqd: 1 },
		{ fieldname: "amount", label: "You will claim (MYR)", reqd: 1, read_only: 1 },
	]
	const item = {
		expense_date: "2026-10-20",
		expense_type: "Mileage (CAR)",
		amount: 0,
		receipt: "/f.jpg",
	}
	assert.equal(hint(item, { shown }), "Fill in Distance (km).")
})

test("a required field the sheet does not show is never named", () => {
	const shown = FIELDS.filter((f) => f.fieldname !== "amount")
	assert.equal(hint({ ...full, amount: 0 }, { shown }), "Fill in the required details.")
})
