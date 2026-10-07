// A sent OT request showed "Hours from check-ins 10.026111111" (owner, HR
// report, 28 Sep 2026): a read-only number sat in a disabled number box with
// every stored decimal. A read-only row reads as words, like a date or yes/no
// already does; hours say at most two decimals, the way the rest of the app does.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readValue } from "../readValue.js"

const date = (v) => `date:${v}`

test("the reported hours read as two decimals at most", () => {
	assert.equal(readValue("Float", 10.026111111, date), "10.03")
})

test("whole and half hours drop the trailing zeros", () => {
	assert.equal(readValue("Float", 3, date), "3")
	assert.equal(readValue("Float", 2.5, date), "2.5")
})

test("a whole number stays whole", () => {
	assert.equal(readValue("Int", 4, date), "4")
})

test("yes/no and dates are unchanged", () => {
	assert.equal(readValue("Check", 1, date), "Yes")
	assert.equal(readValue("Check", 0, date), "No")
	assert.equal(readValue("Date", "2026-09-14", date), "date:2026-09-14")
	assert.equal(readValue("Date", "", date), "")
})

// A sent OT request's "Approved on" sat in a greyed date-time box reading
// "09/24/2026, 05:58:21 PM" (visual baseline, 7 Oct 2026): a read-only
// date-time reads as words like every other row, on the site clock.
test("a read-only date-time is written out, not a disabled box", () => {
	const at = (v) => `at:${v}`
	assert.equal(readValue("Datetime", "2026-09-24 17:58:21", date, at), "at:2026-09-24 17:58:21")
	assert.equal(readValue("Datetime", "", date, at), "")
})
