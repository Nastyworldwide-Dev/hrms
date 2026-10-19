// The All balances ring (owner pick B, 19 Oct 2026): run the arithmetic.
import { test } from "node:test"
import assert from "node:assert/strict"
import { ringArcs } from "../requestsPage.js"

test("left and taken are shares of the year's entitlement", () => {
	// 6 left and 8 taken of 14: the ring is full, 6/14 lime, 8/14 grey.
	assert.deepEqual(ringArcs({ balance: 6, taken: 8, allocated: 14, total: 14 }, 140), {
		left: 60,
		taken: 80,
	})
})

test("a mid-year joiner's ring has a gap where days were never given", () => {
	// 7 given of 14, none used: half the ring is lime, the other half stays track.
	assert.deepEqual(ringArcs({ balance: 7, taken: 0, allocated: 7, total: 14 }, 100), {
		left: 50,
		taken: 0,
	})
})

test("no entitlement draws an empty ring, not NaN", () => {
	assert.deepEqual(ringArcs({ balance: 0, taken: 0, allocated: 0, total: 0 }, 100), {
		left: 0,
		taken: 0,
	})
})

test("the two arcs never overrun the circle", () => {
	// A carry-forward can push balance + taken past the annual entitlement.
	const { left, taken } = ringArcs({ balance: 10, taken: 8, allocated: 18, total: 14 }, 100)
	assert.equal(left, 100 * (10 / 14))
	assert.ok(left + taken <= 100 + 1e-9)
})

test("an older server without taken still draws what is left", () => {
	assert.deepEqual(ringArcs({ balance: 3, allocated: 3, total: 3 }, 30), { left: 30, taken: 0 })
})
