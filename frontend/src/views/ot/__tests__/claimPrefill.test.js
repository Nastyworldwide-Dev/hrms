// The claim box must never open on a nine-decimal figure, and never above the cap.
import { test } from "node:test"
import assert from "node:assert/strict"
import { prefillClaim } from "../claimPrefill.js"

test("a raw punch cap is cut to two decimals, rounded down", () => {
	assert.equal(prefillClaim(8.876944444), 8.87)
	assert.equal(prefillClaim(5.669444444), 5.66)
})

test("the prefill is never above the cap", () => {
	for (const cap of [0.016666667, 1.999999999, 8.876944444, 10.026111111]) {
		assert.ok(prefillClaim(cap) <= cap, String(cap))
	}
})

test("a banded Overtime Pay cap comes through unchanged", () => {
	for (const cap of [0.5, 1, 1.5, 4.5, 8]) assert.equal(prefillClaim(cap), cap)
})

test("an exact two-decimal cap is not dropped a cent by float error", () => {
	assert.equal(prefillClaim(5.67), 5.67)
	assert.equal(prefillClaim(1.15), 1.15)
})

test("no cap stays no cap, so the form's own checks still say why", () => {
	assert.equal(prefillClaim(0), 0)
	assert.ok(Number.isNaN(prefillClaim(undefined)))
	assert.equal(prefillClaim(null), 0)
})

// wiring: the form must prefill through the helper, or the box opens on the raw cap again
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

test("the OT form prefills the claim through prefillClaim, never the raw cap", () => {
	const form = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")
	assert.match(form, /retainedClaim \?\? prefillClaim\(cap\)/)
	assert.doesNotMatch(form, /retainedClaim \?\? cap\b/)
})
