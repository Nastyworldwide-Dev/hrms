// One status rule for every request chip (audit 21 Sep 2026: A-H4, A-M4, C-M-6).
//
// A decided draft — Desk saved status=Approved without submitting — used to
// render "Approved" on the employee's list while no ledger entry existed. And
// three item components each hand-picked a pending word (Open / Draft /
// Pending) that disagreed with the doctype's own Select and its list filter.
// Run: cd frontend && node --test src/utils/__tests__/requestStatus.test.js
import test from "node:test"
import assert from "node:assert/strict"

import { requestStatus, chipVariant } from "../requestStatus.js"

// (doctype, its decision field, the doctype's own pending word) — the same
// table as hrms/api/approval.py DECIDE_THEN_SUBMIT.
const TABLE = [
	["Leave Application", "status", "Open"],
	["Attendance Request", "status", "Open"],
	["OT Request", "status", "Open"],
	["Replacement Leave Claim", "status", "Open"],
	["Compensatory Leave Request", "status", "Open"],
	["Shift Request", "status", "Draft"],
	["Expense Claim", "approval_status", "Draft"],
]

test("a decided draft (Approved, docstatus 0) is still pending and says the doctype's own word", () => {
	for (const [doctype, field, pendingWord] of TABLE) {
		const chip = requestStatus(doctype, { [field]: "Approved", docstatus: 0 })
		assert.equal(chip.label, pendingWord, doctype)
		assert.equal(chip.pending, true, doctype)
		assert.equal(chip.variant, chipVariant(pendingWord), doctype)
		// a plain untouched draft says the same word
		assert.equal(requestStatus(doctype, { [field]: pendingWord, docstatus: 0 }).label, pendingWord)
		assert.equal(requestStatus(doctype, { docstatus: 0 }).label, pendingWord, `${doctype} empty`)
	}
})

test("a submitted decision reads Approved or Rejected, and is no longer pending", () => {
	for (const [doctype, field] of TABLE) {
		const approved = requestStatus(doctype, {
			status: "Unpaid",
			[field]: "Approved",
			docstatus: 1,
		})
		assert.match(approved.label, /^Approved/, doctype)
		assert.equal(approved.pending, false, doctype)
		assert.equal(approved.variant, doctype === "Expense Claim" ? "progress" : "success", doctype)
		const rejected = requestStatus(doctype, { [field]: "Rejected", docstatus: 1 })
		assert.equal(rejected.label, "Rejected", doctype)
		assert.equal(rejected.variant, "danger", doctype)
		assert.equal(rejected.pending, false, doctype)
		assert.equal(requestStatus(doctype, { [field]: "Approved", docstatus: 2 }).label, "Cancelled")
	}
})

test("Expense Claim keeps its payment state after approval", () => {
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Unpaid", docstatus: 1 })
			.label,
		"Approved & Unpaid"
	)
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Paid", docstatus: 1 })
			.label,
		"Paid"
	)
	// get_expense_claims sends no docstatus: `status` says whether it was submitted
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Draft" }).label,
		"Draft"
	)
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Unpaid" }).label,
		"Approved & Unpaid"
	)
})

test("a payload without docstatus trusts the decision field (older list endpoints)", () => {
	assert.equal(requestStatus("Leave Application", { status: "Approved" }).label, "Approved")
	assert.equal(requestStatus("Leave Application", { status: "Approved" }).pending, false)
	assert.equal(requestStatus("Leave Application", { status: "Open" }).pending, true)
	// OT/RL submitted rows from before `status` was in the payload
	assert.equal(requestStatus("OT Request", { docstatus: 1 }).label, "Approved")
})

test("an unknown doctype shows its raw status and nothing when it has none", () => {
	assert.equal(
		requestStatus("Shift Assignment", { status: "Active", docstatus: 1 }).label,
		"Active"
	)
	assert.equal(
		requestStatus("Shift Assignment", { status: "Active", docstatus: 0 }).label,
		"Active"
	)
	assert.equal(requestStatus("Employee Checkin", { docstatus: 0 }).label, "")
	assert.equal(requestStatus("Employee Checkin", {}).label, "")
})

test("the variant is looked up from the English word, never from a translation", () => {
	// the Malay neutral-chip bug: OT/RL translated the label BEFORE the chip
	// looked up its variant, so "Diluluskan" matched nothing and rendered grey.
	const chip = requestStatus("OT Request", { status: "Approved", docstatus: 1 })
	assert.equal(chip.variant, "success")
	assert.equal(chipVariant("Diluluskan"), "neutral")
	assert.equal(chipVariant("approved & unpaid"), "progress")
	assert.equal(chipVariant(undefined), "neutral")
})
