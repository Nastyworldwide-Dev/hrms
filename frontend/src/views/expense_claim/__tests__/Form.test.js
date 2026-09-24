// New Expense Claim renders ONE tab (first field .. `taxes`). In the v16 layout
// `posting_date` sits in the Accounting tab, after `taxes`, so its FormField
// is never mounted and its mount-time default never runs — the model reached
// Save with no posting date and the form's own mandatory check refused it
// ("Posting Date field is mandatory", 15 Sep 2026). The date is seeded on the
// model directly, where no rendering is needed. Source-asserted because the
// node runner does not compile SFCs (see components/__tests__/FormView.test.js).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Form.vue", import.meta.url)), "utf8")

test("a new claim carries today's posting date without a rendered date field", () => {
	const model = src.slice(
		src.indexOf("const expenseClaim = ref({"),
		src.indexOf("})", src.indexOf("const expenseClaim = ref({"))
	)
	assert.match(model, /posting_date:\s*today/, "posting_date must be seeded on the model")
})

test("the seed does not depend on a FormField default that never mounts", () => {
	assert.doesNotMatch(
		src,
		/field\.fieldname === "posting_date"\) field\.default/,
		"posting_date default via field.default is dead code: the field is outside the rendered tab"
	)
})

test("cost tags picked on an expense line survive the claim-level stamp", () => {
	// Form.vue stamps the company cost center onto rows; a row that already
	// carries a cost tag (picked in the item sheet) must keep it.
	assert.doesNotMatch(src, /expense\.cost_center = /, "rows must not be overwritten")
	assert.match(
		src,
		/expense\.cost_center \|\|= /,
		"the claim-level cost center only fills an empty row"
	)
})

// Owner ruling Q4 (delegated, 24 Sep 2026): the employee is not asked for a
// "Posting date". It is the accounting date of the claim; each expense line
// carries its own date, and the model is seeded with today (above).
test("the form does not ask for a posting date", () => {
	const fields = src.slice(src.indexOf("const FIELDS = ["), src.indexOf("]", src.indexOf("const FIELDS = [")))
	assert.doesNotMatch(fields, /"posting_date"/)
})

test("the running total is shown once (the Expenses header), not in three boxes", () => {
	const fields = src.slice(src.indexOf("const FIELDS = ["), src.indexOf("]", src.indexOf("const FIELDS = [")))
	for (const f of ["total_claimed_amount", "total_sanctioned_amount", "grand_total"]) {
		assert.doesNotMatch(fields, new RegExp(`"${f}"`))
	}
	assert.match(src, /expenseClaim\.value\.total_claimed_amount = total_claimed_amount/, "still computed for the server")
})
