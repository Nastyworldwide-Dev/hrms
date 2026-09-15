// The New Expense Item sheet renders its cost tags (Cost Center + Accounting
// Dimensions) from the fenced hrms.api.get_expense_cost_tags payload through
// withCostTagFields, and a tag the employee picked on the line is never
// clobbered by the claim-level stamp. Source-asserted because the node runner
// does not compile SFCs (see FormView.test.js).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../ExpensesTable.vue", import.meta.url)), "utf8")

test("the sheet's fields go through withCostTagFields with the fenced cost tags", () => {
	assert.match(src, /import \{ withCostTagFields \} from "@\/utils\/expenseCostTags"/)
	assert.match(src, /url: "hrms\.api\.get_expense_cost_tags"/)
	assert.match(src, /withCostTagFields\([\s\S]*?costTags\.data\s*\)/)
})

test("changing the expense type fills an empty cost center, never overwrites a picked one", () => {
	assert.doesNotMatch(src, /expenseItem\.value\.cost_center = /)
	assert.match(src, /expenseItem\.value\.cost_center \|\|= /)
})
