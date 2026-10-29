// The GL account an expense line posts to is its own read-only row under Type
// (owner, 29 Oct 2026): it used to be "GL: Travel Expenses" typed into the
// Description, where staff could edit it.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

import { withGlAccountField, GL_FIELD } from "../expenseGlAccount.js"

const FIELDS = [
	{ fieldname: "expense_date", fieldtype: "Date", label: "Expense Date" },
	{ fieldname: "expense_type", fieldtype: "Link", label: "Type" },
	{ fieldname: "description", fieldtype: "Small Text", label: "Description" },
	{ fieldname: "amount", fieldtype: "Currency", label: "Amount" },
]

test("the GL row sits right after Type, read-only", () => {
	const out = withGlAccountField(FIELDS, "Travel Expenses")
	const names = out.map((f) => f.fieldname)
	assert.deepEqual(names, ["expense_date", "expense_type", GL_FIELD, "description", "amount"])
	const row = out.find((f) => f.fieldname === GL_FIELD)
	assert.equal(row.read_only, 1)
	assert.equal(row.label, "GL account")
	assert.equal(row.default, "Travel Expenses")
})

test("no type picked yet: no GL row", () => {
	assert.deepEqual(
		withGlAccountField(FIELDS, null).map((f) => f.fieldname),
		FIELDS.map((f) => f.fieldname)
	)
})

test("the label is translated", () => {
	const out = withGlAccountField(FIELDS, "Travel Expenses", (t) => `~${t}`)
	assert.equal(out.find((f) => f.fieldname === GL_FIELD).label, "~GL account")
})

test("the expense sheet uses it, and no longer copies the type's description", () => {
	const src = readFileSync(new URL("../../components/ExpensesTable.vue", import.meta.url), "utf8")
	assert.match(src, /withGlAccountField\(/)
	assert.doesNotMatch(
		src,
		/expenseItem\.value\.description = claimTypesByID\[value\]\?\.description/
	)
})

test("the GL row is never sent as part of the line", () => {
	const src = readFileSync(new URL("../../components/ExpensesTable.vue", import.meta.url), "utf8")
	assert.match(src, /delete [^\n]*\[GL_FIELD\]|GL_FIELD[^\n]*delete/)
})
