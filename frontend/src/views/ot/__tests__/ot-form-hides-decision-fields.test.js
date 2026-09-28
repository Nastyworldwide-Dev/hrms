// A new OT claim never offers the fields set after the decision: when it was
// approved (the system) and whether HR has paid it (HR) — 28 Sep 2026.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

const form = readFileSync(new URL("../OTRequestForm.vue", import.meta.url), "utf8")

test("a new claim does not offer Approved On or Payment", () => {
	const filter = form.slice(
		form.indexOf("const formFields = createResource"),
		form.indexOf("const canEditClaim")
	)
	assert.match(filter, /"approved_on"/)
	assert.match(filter, /"payment_status"/)
})
