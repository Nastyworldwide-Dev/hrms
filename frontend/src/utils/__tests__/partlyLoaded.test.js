// "Your last 5" says one of its lists is missing (alpha.41 S7). Behaviour, not source text
// (review of 63d347a20): which states show the line, and that a retry keeps it until it settles.
import { test } from "node:test"
import assert from "node:assert/strict"
import { partlyLoaded } from "../partlyLoaded.js"

const ok = { error: null, loading: false }
const failed = { error: new Error("boom"), loading: false }
const retrying = { error: null, loading: true, retrying: true }

test("rows on screen and one list failed: say so", () => {
	assert.equal(partlyLoaded(3, [ok, failed, ok]), true)
})

test("rows and every list fine: say nothing", () => {
	assert.equal(partlyLoaded(3, [ok, ok]), false)
})

test("no rows: the list's own empty or error state speaks, not this line", () => {
	assert.equal(partlyLoaded(0, [failed]), false)
})

test("while a failed list is being retried the line stays, so a tap never looks like nothing", () => {
	// frappe-ui clears `error` when a fetch starts; `retrying` is the panel's own mark
	assert.equal(partlyLoaded(3, [ok, retrying]), true)
})

test("a list that loads for the first time is not a failure", () => {
	assert.equal(partlyLoaded(3, [ok, { error: null, loading: true }]), false)
})
