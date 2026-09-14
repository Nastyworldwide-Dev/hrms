// Owner ruling, 14 Sep 2026: HR and the request's approver may cancel an approved
// request; the employee (and anyone else) may not. The server guard decides; this
// keeps the PWA from offering a Cancel that can only fail.
// Run: cd frontend && node --test src/utils/__tests__/cancelRule.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

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
	for (const doctype of ["Leave Application", "Shift Request", "OT Request"]) {
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

test("HR roles may cancel an approved request of any type", () => {
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
				"approver",
				`${role} ${doctype}`
			)
		}
})

test("the named approver may cancel an approved request", () => {
	const viewer = { user: "boss@example.com", roles: ["Employee"], employee: "EMP-BOSS" }
	for (const [doctype, field] of [
		["Leave Application", "leave_approver"],
		["Expense Claim", "expense_approver"],
		["Shift Request", "approver"],
	]) {
		const doc = approved(doctype, { [field]: "boss@example.com" })
		assert.equal(canOfferCancel(doc, doctype, viewer), "approver", doctype)
		assert.equal(canOfferCancel(approved(doctype), doctype, viewer), false, `${doctype} not named`)
	}
})

test("the employee never gets Cancel on their own approved request, even as HR or approver", () => {
	assert.equal(canOfferCancel(approved("Leave Application"), "Leave Application", STAFF), false)
	const hrSelf = { ...STAFF, roles: ["HR Manager"] }
	const doc = approved("Leave Application", { leave_approver: STAFF.user })
	assert.equal(canOfferCancel(doc, "Leave Application", hrSelf), false)
	assert.equal(canOfferCancel(approved("Employee Advance"), "Employee Advance", hrSelf), false)
})

test("an unrelated employee gets no Cancel on an approved request", () => {
	for (const doctype of ["Leave Application", "OT Request", "Travel Request"])
		assert.equal(canOfferCancel(approved(doctype), doctype, OTHER), false, doctype)
	assert.equal(canOfferCancel(approved("Leave Application"), "Leave Application"), false)
})

test("Expense Claim decides in approval_status", () => {
	const doc = {
		doctype: "Expense Claim",
		docstatus: 1,
		approval_status: "Approved",
		status: "Unpaid",
	}
	assert.equal(canOfferCancel(doc, "Expense Claim", OTHER), false)
	assert.equal(canOfferCancel(doc, "Expense Claim", { ...OTHER, roles: ["HR User"] }), "approver")
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
	const hr = { user: "hr@example.com", roles: ["HR User"] }
	assert.equal(
		canOfferCancel({ docstatus: 1, status: "Approved" }, "Leave Application", OTHER),
		false
	)
	assert.equal(
		canOfferCancel({ docstatus: 1, approval_status: "Approved" }, "Expense Claim", hr),
		"approver"
	)
})

test("both Cancel buttons apply the rule with the viewer", () => {
	const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
	const offer =
		/cancelOffer === "approver" \|\|\s*\(cancelOffer === "own" && hasPermission\("cancel"\)\)/
	const sheet = read("../../components/RequestActionSheet.vue")
	assert.match(sheet, /import \{ canOfferCancel \} from "@\/utils\/cancelRule"/)
	assert.match(
		sheet,
		/canOfferCancel\(document\.doc, props\.modelValue\?\.doctype, cancelViewer\.value\)/
	)
	assert.match(sheet.replaceAll("'", '"'), offer)
	const form = read("../../components/FormView.vue")
	assert.match(form, /import \{ canOfferCancel \} from "@\/utils\/cancelRule"/)
	assert.match(form, /canOfferCancel\(formModel\.value, props\.doctype, cancelViewer\.value\)/)
	assert.match(form, offer)
})
