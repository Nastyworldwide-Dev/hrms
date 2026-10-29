// The GL account an expense line posts to is its own read-only row under Type
// (owner, 29 Oct 2026): it used to be "GL: Travel Expenses" typed into the
// Description, where staff could edit it.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

import { withGlAccountField, withoutGlAccount, GL_FIELD } from "../expenseGlAccount.js"

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

test("the GL row is taken off the line before it is saved, without touching the sheet's copy", () => {
	const shown = { expense_type: "Travel", amount: 10, [GL_FIELD]: "Travel Expenses" }
	const saved = withoutGlAccount(shown)
	assert.equal(GL_FIELD in saved, false)
	assert.deepEqual(saved, { expense_type: "Travel", amount: 10 })
	assert.equal(shown[GL_FIELD], "Travel Expenses")
})

test("both ways a line leaves the sheet go through withoutGlAccount", () => {
	const src = readFileSync(new URL("../../components/ExpensesTable.vue", import.meta.url), "utf8")
	const save = src.slice(
		src.indexOf("const updateExpenseItem"),
		src.indexOf("resetSelectedItem()", src.indexOf("const updateExpenseItem"))
	)
	assert.match(save, /withoutGlAccount\(expenseItem\.value\)/)
	assert.doesNotMatch(save, /emit\([^)]*expenseItem\.value/)
})

test("editing a saved line shows its GL row too (the type did not change, so no watcher fires)", () => {
	const src = readFileSync(new URL("../../components/ExpensesTable.vue", import.meta.url), "utf8")
	const open = src.slice(src.indexOf("const openModal"), src.indexOf("const deleteExpenseItem"))
	assert.match(open, /\[GL_FIELD\]\s*[:=]\s*claimTypesByID\[item\.expense_type\]\?\.gl_account/)
})
