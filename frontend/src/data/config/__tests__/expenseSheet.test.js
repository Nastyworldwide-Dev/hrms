// The approver's expense sheet (alpha.6 screen journey, 24 Sep 2026) listed
// Posting Date, Total Claimed, Total Sanctioned, Total Taxes and Charges,
// Total Advance Amount, Grand Total, then Status "Draft" AND Approval Status
// "Waiting": ERP words, zeros for features this company does not use
// (advances are hidden by owner ruling, 15 Sep), and two statuses for one
// request. The approver needs: who, the items, the total, and one status.
import { test } from "node:test"
import assert from "node:assert/strict"

import { EXPENSE_CLAIM_FIELDS } from "../requestSummaryFields.js"

const names = EXPENSE_CLAIM_FIELDS.map((f) => f.fieldname)

test("one status on the sheet: the decision", () => {
	assert.ok(names.includes("approval_status"))
	assert.ok(!names.includes("status"), "'Draft' beside 'Waiting' is a second, contradicting status")
})

test("no accounting-only rows", () => {
	for (const f of [
		"posting_date",
		"total_taxes_and_charges",
		"total_advance_amount",
		"total_sanctioned_amount",
		"grand_total",
	]) {
		assert.ok(!names.includes(f), `${f} is not something an approver decides on`)
	}
})

test("the approver sees who, what and how much", () => {
	assert.deepEqual(names, ["employee", "expenses", "total_claimed_amount", "approval_status"])
	assert.equal(EXPENSE_CLAIM_FIELDS.find((f) => f.fieldname === "total_claimed_amount").label, "Total")
})
