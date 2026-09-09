// The employee is forced to write an Explanation on an OT Request and a
// Replacement Leave Claim; the approver's review sheet then hid it, and hid
// the decision too. The sheet renders exactly REQUEST_SUMMARY_FIELDS.
// Run: cd frontend && node --test tests/request-summary-explanation.test.mjs
import test from "node:test"
import assert from "node:assert/strict"

import {
	OT_REQUEST_FIELDS,
	REPLACEMENT_LEAVE_CLAIM_FIELDS,
	REQUEST_SUMMARY_FIELDS,
} from "../src/data/config/requestSummaryFields.js"

for (const [doctype, fields] of [
	["OT Request", OT_REQUEST_FIELDS],
	["Replacement Leave Claim", REPLACEMENT_LEAVE_CLAIM_FIELDS],
]) {
	test(`${doctype} review summary shows the explanation and the decision`, () => {
		assert.equal(REQUEST_SUMMARY_FIELDS[doctype], fields)
		const explanation = fields.find((f) => f.fieldname === "explanation")
		assert.deepEqual(explanation, {
			fieldname: "explanation",
			label: "Explanation",
			fieldtype: "Small Text",
		})
		const status = fields.find((f) => f.fieldname === "status")
		assert.ok(status, "status entry present")
		assert.equal(status.label, "Status")
		assert.equal(status.fieldtype, "Select")
	})
}
