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

test("Project is not asked on an expense line (owner, 14 Oct 2026)", () => {
	assert.match(src, /fieldname !== "project"/)
})

test("a mileage type asks km and prices the line from the type's rate", () => {
	assert.match(
		src,
		/withMileageFields\(\s*expensesTableFields\.data \|\| \[\],\s*mileageRate\.value,\s*expenseItem\.value\.expense_type/
	)
	assert.match(src, /claimTypesByID\[expenseItem\.value\.expense_type\]\?\.rate_per_km/)
	assert.match(src, /expenseItem\.value\.amount = mileageAmount\(km, rate\)/)
})

test("a mileage line says its distance in the list", () => {
	assert.match(src, /item\.distance_km \? __\("\{0\} km"/)
})

// Coherence gate, 25 Oct 2026: a new claim showed two lime buttons, "Add expense" and "Send"
// (§18: one filled action per screen). Send is the screen's action; the first Add is the
// secondary, ghost style, still a labelled button (UX review 21 Oct, F4).
test("the empty list's Add expense is a ghost button, not a second filled action", () => {
	const empty = src.match(/<GEmptyState[\s\S]*?<\/GEmptyState>/)?.[0] ?? ""
	assert.match(empty, /<GGhostButton :label="__\('Add expense'\)"/)
	assert.doesNotMatch(empty, /<GButton\b/)
})
