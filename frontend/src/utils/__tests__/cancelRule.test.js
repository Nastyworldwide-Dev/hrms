// Owner rule: an approved request is never cancelled. The PWA must not offer
// Cancel for one; a rejected request stays cancellable.
// Run: cd frontend && node --test src/utils/__tests__/cancelRule.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

import { canOfferCancel } from "../cancelRule.js"

test("approved status hides Cancel; rejected keeps it", () => {
	for (const doctype of [
		"Leave Application",
		"OT Request",
		"Shift Request",
		"Replacement Leave Claim",
	]) {
		assert.equal(canOfferCancel({ doctype, docstatus: 1, status: "Approved" }), false, doctype)
		assert.equal(canOfferCancel({ doctype, docstatus: 1, status: "Rejected" }), true, doctype)
	}
})

test("Expense Claim decides in approval_status", () => {
	const doc = { doctype: "Expense Claim", docstatus: 1 }
	assert.equal(canOfferCancel({ ...doc, approval_status: "Approved", status: "Unpaid" }), false)
	assert.equal(canOfferCancel({ ...doc, approval_status: "Rejected", status: "Rejected" }), true)
})

test("types without a decision field are approved by submission", () => {
	for (const doctype of ["Compensatory Leave Request", "Employee Advance", "Travel Request"]) {
		assert.equal(canOfferCancel({ doctype, docstatus: 1, status: "Unpaid" }), false, doctype)
	}
})

test("only a submitted document can be cancelled at all", () => {
	assert.equal(canOfferCancel({ doctype: "OT Request", docstatus: 0, status: "Open" }), false)
	assert.equal(canOfferCancel({ doctype: "OT Request", docstatus: 2, status: "Rejected" }), false)
	assert.equal(canOfferCancel(undefined), false)
})

test("doctype may be passed when the doc does not carry it", () => {
	assert.equal(canOfferCancel({ docstatus: 1 }, "Travel Request"), false)
	assert.equal(
		canOfferCancel({ docstatus: 1, approval_status: "Approved" }, "Expense Claim"),
		false
	)
})

test("both Cancel buttons apply the rule", () => {
	const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
	const sheet = read("../../components/RequestActionSheet.vue")
	assert.match(sheet, /import \{ canOfferCancel \} from "@\/utils\/cancelRule"/)
	assert.match(
		sheet,
		/canOfferCancel\(document\.doc, props\.modelValue\?\.doctype\) &&\s*hasPermission\('cancel'\)/
	)
	const form = read("../../components/FormView.vue")
	assert.match(form, /import \{ canOfferCancel \} from "@\/utils\/cancelRule"/)
	assert.match(
		form,
		/canOfferCancel\(formModel\.value, props\.doctype\) && hasPermission\("cancel"\)/
	)
})
