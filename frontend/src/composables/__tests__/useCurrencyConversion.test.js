// Currency field labels must never read "Amount (undefined)". The immediate
// watcher runs before a company/currency is picked on a new expense claim, so
// updateLabels() has to tolerate a missing (or null) docRef.value.currency.
import { test } from "node:test"
import assert from "node:assert/strict"
import { ref, reactive } from "vue"

import { useCurrencyConversion } from "../useCurrencyConversion.js"

test("shows a plain label, not (undefined), before a currency is set", () => {
	const formFields = reactive({ data: [{ fieldname: "amount", label: "Amount" }] })
	const docRef = ref({ currency: undefined })
	const { updateLabels } = useCurrencyConversion(formFields, docRef, ["amount"])
	updateLabels()
	assert.equal(formFields.data[0].label, "Amount")
})

test("appends the currency once one is chosen", () => {
	const formFields = reactive({ data: [{ fieldname: "amount", label: "Amount" }] })
	const docRef = ref({ currency: "MYR" })
	const { updateLabels } = useCurrencyConversion(formFields, docRef, ["amount"])
	updateLabels()
	assert.equal(formFields.data[0].label, "Amount (MYR)")
})

test("does not throw when docRef.value is null", () => {
	const formFields = reactive({ data: [{ fieldname: "amount", label: "Amount" }] })
	const docRef = ref(null)
	assert.doesNotThrow(() => {
		const { updateLabels } = useCurrencyConversion(formFields, docRef, ["amount"])
		updateLabels()
	})
	assert.equal(formFields.data[0].label, "Amount")
})
