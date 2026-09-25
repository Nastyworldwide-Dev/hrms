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

// (doctype, its decision field, the doctype's own STORED pending word) — the
// same table as hrms/api/approval.py DECIDE_THEN_SUBMIT. The stored word is
// what the DB holds and what a list filter sends; it is NOT what the chip says.
const TABLE = [
	["Leave Application", "status", "Open"],
	["Attendance Request", "status", "Open"],
	["OT Request", "status", "Open"],
	["Replacement Leave Claim", "status", "Open"],
	["Compensatory Leave Request", "status", "Open"],
	["Shift Request", "status", "Draft"],
	["Expense Claim", "approval_status", "Draft"],
	["Remote Checkin Request", "status", "Pending"],
]

// One waiting word on screen. The DB still holds Open / Draft / Pending per
// doctype (three words for one state, audit A-M4); the employee is shown one.
const WAITING = "Waiting"

test("a decided draft (Approved, docstatus 0) is still pending and says ONE waiting word", () => {
	for (const [doctype, field, pendingWord] of TABLE) {
		const chip = requestStatus(doctype, { [field]: "Approved", docstatus: 0 })
		assert.equal(chip.label, WAITING, doctype)
		assert.equal(chip.pending, true, doctype)
		assert.equal(chip.variant, "attention", doctype)
		// a plain untouched draft says the same word, whatever the DB holds
		assert.equal(requestStatus(doctype, { [field]: pendingWord, docstatus: 0 }).label, WAITING)
		assert.equal(requestStatus(doctype, { docstatus: 0 }).label, WAITING, `${doctype} empty`)
	}
})

test("the stored pending word is never rewritten — only what the screen says changes", () => {
	// A regression here would be a data migration wearing a wording fix's
	// clothes: filters, list views and existing rows all read the stored word.
	for (const [doctype, field, pendingWord] of TABLE) {
		const doc = { [field]: pendingWord, docstatus: 0 }
		requestStatus(doctype, doc)
		assert.equal(doc[field], pendingWord, `${doctype} document was mutated`)
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
		// alpha.6 W1: the person's words, not finance's "Approved & Unpaid".
		"Approved, not paid yet"
	)
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Paid", docstatus: 1 })
			.label,
		"Paid"
	)
	// get_expense_claims sends no docstatus: `status` says whether it was submitted
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Draft" }).label,
		WAITING
	)
	assert.equal(
		requestStatus("Expense Claim", { approval_status: "Approved", status: "Unpaid" }).label,
		"Approved, not paid yet"
	)
})

test("a payload without docstatus trusts the decision field (older list endpoints)", () => {
	assert.equal(requestStatus("Leave Application", { status: "Approved" }).label, "Approved")
	assert.equal(requestStatus("Leave Application", { status: "Approved" }).pending, false)
	assert.equal(requestStatus("Leave Application", { status: "Open" }).pending, true)
	assert.equal(requestStatus("Leave Application", { status: "Open" }).label, WAITING)
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

test("Employee Issue states carry colour — a finished issue does not look untouched", () => {
	// IssueList renders the raw Employee Issue status through GStatusChip, and
	// `in progress` / `completed` had no entry, so both fell through to grey.
	assert.equal(chipVariant("In Progress"), "progress")
	assert.equal(chipVariant("Completed"), "success")
	assert.equal(chipVariant("Open"), "attention")
})

test("a remote check-in row reads the same rule as every other request", () => {
	// RemoteApprovals hand-rolled its chip on `status === 'Approved'`, so a
	// Rejected punch rendered identically to a Pending one.
	const rejected = requestStatus("Remote Checkin Request", { status: "Rejected" })
	assert.equal(rejected.label, "Rejected")
	assert.equal(rejected.variant, "danger")
	assert.equal(rejected.pending, false)
	const approved = requestStatus("Remote Checkin Request", { status: "Approved" })
	assert.equal(approved.label, "Approved")
	assert.equal(approved.variant, "success")
	// not submittable: it has no docstatus at all, so the decision field decides
	assert.equal(requestStatus("Remote Checkin Request", { status: "Pending" }).label, WAITING)
})

// Reported 25 Sep 2026 ("2 fix a day still Open"): On Duty requests
// submitted before the Approve/Reject field existed (or in the old system)
// carry status "Open" with docstatus 1. For these types submitting IS the
// approval (the controller only pays out on submit), and the Approved filter
// already counted them — only the chip said "Open".
test("a submitted request still labelled Open reads Approved", () => {
	for (const doctype of ["Attendance Request", "OT Request", "Replacement Leave Claim", "Leave Application"]) {
		const s = requestStatus(doctype, { status: "Open", docstatus: 1 })
		assert.equal(s.label, "Approved", doctype)
		assert.equal(s.pending, false)
	}
	assert.equal(requestStatus("Shift Request", { status: "Draft", docstatus: 1 }).label, "Approved")
})
