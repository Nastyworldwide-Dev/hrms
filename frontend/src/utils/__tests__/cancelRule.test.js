// Owner ruling, 14 Sep 2026: HR and the request's approver (named or reports_to)
// may cancel an approved request; the employee (and anyone else) may not. For an
// approved request the PWA asks the server (can_cancel_approved) — this rule only
// says whether to ask.
// Run: cd frontend && node --test src/utils/__tests__/cancelRule.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { canOfferCancel } from "../cancelRule.js"

const STAFF = { user: "staff@example.com", roles: ["Employee"], employee: "EMP-STAFF" }
const OTHER = { user: "other@example.com", roles: ["Employee"], employee: "EMP-OTHER" }
const HR = ["HR User", "HR Manager", "System Manager"]
const approved = (doctype, extra = {}) => ({
	doctype,
	docstatus: 1,
	status: "Approved",
	approval_status: "Approved",
	employee: "EMP-STAFF",
	...extra,
})

test("a submitted request that is not approved is the cancel permission's call", () => {
	// Compensatory Leave Request decides in `status` since 15 Sep 2026 ("yes add
	// that reject button"): a rejection is submitted too, and granted nothing.
	for (const doctype of [
		"Leave Application",
		"Shift Request",
		"OT Request",
		"Compensatory Leave Request",
	]) {
		const doc = { doctype, docstatus: 1, status: "Rejected", employee: "EMP-STAFF" }
		assert.equal(canOfferCancel(doc, doctype, STAFF), "own", doctype)
		assert.equal(canOfferCancel(doc, doctype, OTHER), "own", doctype)
	}
	const claim = {
		doctype: "Expense Claim",
		docstatus: 1,
		approval_status: "Rejected",
		status: "Approved",
	}
	assert.equal(canOfferCancel(claim, "Expense Claim", OTHER), "own")
})

test("an approved request of any type is referred to the server for non-employees", () => {
	const types = [
		"Leave Application",
		"Expense Claim",
		"Shift Request",
		"OT Request",
		"Attendance Request",
		"Replacement Leave Claim",
		"Compensatory Leave Request",
		"Employee Advance",
		"Travel Request",
	]
	for (const role of HR)
		for (const doctype of types) {
			const viewer = { user: "hr@example.com", roles: ["Employee", role], employee: "EMP-HR" }
			assert.equal(
				canOfferCancel(approved(doctype), doctype, viewer),
				"approved",
				`${role} ${doctype}`
			)
		}
})

test("a reports_to manager with no approver field is referred to the server", () => {
	const manager = { user: "boss@example.com", roles: ["Employee"], employee: "EMP-BOSS" }
	for (const doctype of [
		"Leave Application",
		"OT Request",
		"Attendance Request",
		"Travel Request",
	])
		assert.equal(canOfferCancel(approved(doctype), doctype, manager), "approved", doctype)
})

test("the employee never gets Cancel on their own approved request, even as HR or approver", () => {
	assert.equal(canOfferCancel(approved("Leave Application"), "Leave Application", STAFF), false)
	const hrSelf = { ...STAFF, roles: ["HR Manager"] }
	const doc = approved("Leave Application", { leave_approver: STAFF.user })
	assert.equal(canOfferCancel(doc, "Leave Application", hrSelf), false)
	assert.equal(canOfferCancel(approved("Employee Advance"), "Employee Advance", hrSelf), false)
})

test("Expense Claim decides in approval_status", () => {
	const doc = {
		doctype: "Expense Claim",
		docstatus: 1,
		approval_status: "Approved",
		status: "Unpaid",
	}
	assert.equal(canOfferCancel(doc, "Expense Claim", OTHER), "approved")
	assert.equal(
		canOfferCancel({ ...doc, approval_status: "Rejected" }, "Expense Claim", OTHER),
		"own"
	)
})

test("only a submitted document can be cancelled at all", () => {
	const hr = { user: "hr@example.com", roles: ["HR Manager"] }
	assert.equal(
		canOfferCancel({ doctype: "OT Request", docstatus: 0, status: "Open" }, "OT Request", hr),
		false
	)
	assert.equal(
		canOfferCancel({ doctype: "OT Request", docstatus: 2, status: "Approved" }, "OT Request", hr),
		false
	)
	assert.equal(canOfferCancel(undefined), false)
})

test("doctype may be passed when the doc does not carry it", () => {
	assert.equal(
		canOfferCancel({ docstatus: 1, status: "Approved" }, "Leave Application", OTHER),
		"approved"
	)
	assert.equal(
		canOfferCancel({ docstatus: 1, approval_status: "Draft" }, "Expense Claim", OTHER),
		"own"
	)
})
