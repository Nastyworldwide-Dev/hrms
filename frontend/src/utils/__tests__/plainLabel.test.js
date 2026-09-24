// alpha.6 C1. Form labels come straight from the doctype ("Leave Type",
// "Expense Approver", "Explanation", "OT Date", "Claimed Hours", "Sanctioned
// Amount", "Total leave days", "Leave balance before application"): the ERP's
// words, measured on the live forms (alpha6-pages.md §F). Apple HIG Writing:
// plain, familiar words; GOV.UK: no jargon. ONE table, applied to every field
// label, so a form cannot bring the ERP word back.
import { test } from "node:test"
import assert from "node:assert/strict"

import { plainLabel, PLAIN_LABELS } from "../plainLabel.js"

test("the ERP words on the forms become the person's words", () => {
	const cases = {
		"Leave Type": "Kind of leave",
		"Leave Approver": "Goes to",
		"Expense Approver": "Goes to",
		Approver: "Goes to",
		"From Date": "From",
		"To Date": "To",
		Explanation: "Note",
		"OT Date": "Day you worked",
		"Claimed Hours": "Hours",
		"Shift Type": "New shift",
		"Expense Claim Type": "Type",
		"Sanctioned Amount": "Approved amount",
		"Total Leave Days": "Days",
		"Leave Balance Before Application": "Days left before this",
		"Expense Date": "Date",
		"In Time": "In",
		"Out Time": "Out",
	}
	for (const [erp, plain] of Object.entries(cases)) assert.equal(plainLabel(erp), plain, erp)
})

test("matching ignores case, so Title Case and sentence case both map", () => {
	assert.equal(plainLabel("leave type"), "Kind of leave")
})

test("an unknown label passes through untouched", () => {
	assert.equal(plainLabel("Half Day"), "Half Day")
	assert.equal(plainLabel(""), "")
	assert.equal(plainLabel(undefined), "")
})

test("no plain word is itself jargon", () => {
	for (const plain of Object.values(PLAIN_LABELS)) {
		assert.doesNotMatch(plain, /approver|explanation|posting|sanctioned|claim type|\bOT\b/i, plain)
	}
})
