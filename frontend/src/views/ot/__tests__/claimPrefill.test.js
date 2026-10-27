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

test("the OT form prefills the claim through claimAfterCheck (prefillClaim), never the raw cap", () => {
	const form = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")
	assert.match(form, /claimed_hours: claimAfterCheck\(\{[\s\S]*?retained: retainedClaim,\s*cap,\s*\}\)/)
	assert.doesNotMatch(form, /retainedClaim \?\? cap\b/)
})

// Regression, 27 Oct 2026 (owner): picking a claimable day left Hours empty. Since 21 Oct
// (9bf8f6b6d) the Hours row appears only once a day is picked, so its FormField mounts then and
// seeds "" before the day check answers; the merge kept "" because `??` replaces only
// null/undefined. "" and null both mean "nothing claimed yet".
import { claimAfterCheck } from "../claimPrefill.js"

test("a picked day's hours fill the box even after the row seeded it empty", () => {
	assert.equal(claimAfterCheck({ current: "", retained: null, cap: 2 }), 2)
	assert.equal(claimAfterCheck({ current: null, retained: null, cap: 4.5 }), 4.5)
	assert.equal(claimAfterCheck({ current: undefined, retained: null, cap: 8.876944444 }), 8.87)
})

test("a saved claim reopened keeps its own hours", () => {
	assert.equal(claimAfterCheck({ current: 1.5, retained: null, cap: 2 }), 1.5)
	assert.equal(claimAfterCheck({ current: "", retained: 1, cap: 2 }), 1)
})
