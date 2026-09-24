// Owner ruling Q1 (24 Sep 2026): a new request's button says "Send to {name}",
// not "Save". Apple HIG Buttons / Writing: a label is a verb naming the
// result ("Send"), and a request that goes to a person names the person.
import { test } from "node:test"
import assert from "node:assert/strict"

import { sendLabel } from "../sendLabel.js"

const fields = [
	{
		fieldname: "leave_approver",
		documentList: [
			{ value: "hafiz@x.com", label: "Muhammad Nur Hafiz" },
			{ value: "ali@x.com", label: "Ali" },
		],
	},
]

test("a new request routed to a chosen person: Send to their first name", () => {
	assert.equal(
		sendLabel({ doctype: "Leave Application", isNew: true, fields, model: { leave_approver: "hafiz@x.com" } }),
		"Send to Muhammad"
	)
})

test("no approver picked yet, or a type with no approver field: Send", () => {
	assert.equal(sendLabel({ doctype: "Leave Application", isNew: true, fields, model: {} }), "Send")
	assert.equal(sendLabel({ doctype: "OT Request", isNew: true, fields: [], model: {} }), "Send")
})

test("not a request, or editing an existing one: Save stays", () => {
	assert.equal(sendLabel({ doctype: "Employee Issue", isNew: true, fields, model: {} }), "Send to HR")
	assert.equal(sendLabel({ doctype: "Leave Application", isNew: false, fields, model: {} }), "Save")
	assert.equal(sendLabel({ doctype: "Shift Assignment", isNew: true, fields, model: {} }), "Save")
})
