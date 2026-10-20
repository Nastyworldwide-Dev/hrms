// Mileage preview on an expense line (owner, 14 Oct 2026).
// Run: cd frontend && node --test src/utils/__tests__/expenseMileage.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import {
	missingRateNote,
	mileageAmount,
	mileageExplainer,
	withMileageFields,
} from "../expenseMileage.js"

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
	assert.equal(amount.class, "g-form-row--claim")
})

test("an ordinary type does not ask the distance and leaves the amount editable", () => {
	const out = withMileageFields(FIELDS, 0)
	assert.deepEqual(
		out.map((f) => f.fieldname),
		["expense_type", "amount"]
	)
	assert.equal(out[1].read_only, undefined)
})

test("the explainer says the amount in money, not only the rate", () => {
	const rm = (n) => `RM ${n.toFixed(2)}`
	assert.equal(mileageExplainer(50, 0.6, rm), "50 km × RM 0.60 per km = RM 30.00")
	assert.equal(mileageExplainer(0, 0.6, rm), "")
	assert.equal(mileageExplainer(70, 0, rm), "")
})

test("the claimed amount keeps its currency in the label", () => {
	const fields = [{ fieldname: "distance_km" }, { fieldname: "amount", label: "Amount (MYR)" }]
	assert.equal(withMileageFields(fields, 0.6)[1].label, "You will claim (MYR)")
	assert.equal(
		withMileageFields([{ fieldname: "amount", label: "Amount" }], 0.6)[0].label,
		"You will claim"
	)
})

test("a mileage type with no rate still asks the distance (optional) and says why there is no price", () => {
	const out = withMileageFields(FIELDS, 0, "Mileage (CAR) (MILEAGE CAR)")
	assert.deepEqual(
		out.map((f) => f.fieldname),
		["expense_type", "distance_km", "amount"]
	)
	assert.equal(out[1].reqd, 0)
	assert.equal(out[2].read_only, undefined)
	assert.equal(
		missingRateNote(0, "Mileage (Motorcycle)"),
		"HR has not set a rate for this type yet. Type the amount."
	)
	assert.equal(missingRateNote(0.6, "Mileage (Motorcycle)"), "")
	assert.equal(missingRateNote(0, "Parking"), "")
})
