// Mileage preview on an expense line (owner, 14 Oct 2026).
// Run: cd frontend && node --test src/utils/__tests__/expenseMileage.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { mileageAmount, withMileageFields } from "../expenseMileage.js"

const FIELDS = [
	{ fieldname: "expense_type", fieldtype: "Link", reqd: 1 },
	{ fieldname: "distance_km", fieldtype: "Float" },
	{ fieldname: "amount", fieldtype: "Currency", reqd: 1, label: "Amount" },
]

test("the amount is km x rate, rounded to cents", () => {
	assert.equal(mileageAmount(70, 0.6), 42)
	assert.equal(mileageAmount("12.5", 0.33), 4.13)
	assert.equal(mileageAmount("", 0.6), 0)
	assert.equal(mileageAmount(-5, 0.6), 0)
})

test("a mileage type asks the distance and shows the amount read-only", () => {
	const [, km, amount] = withMileageFields(FIELDS, 0.6)
	assert.equal(km.reqd, 1)
	assert.equal(amount.read_only, 1)
	assert.equal(amount.label, "You will claim")
})

test("an ordinary type does not ask the distance and leaves the amount editable", () => {
	const out = withMileageFields(FIELDS, 0)
	assert.deepEqual(
		out.map((f) => f.fieldname),
		["expense_type", "amount"]
	)
	assert.equal(out[1].read_only, undefined)
})
