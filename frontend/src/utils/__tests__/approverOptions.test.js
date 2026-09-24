// A picker shows people by NAME. The approver pickers on Time off, Expense and
// Shift change showed "muhammadnurhafiz@nastyworldwide.com : H…" (owner
// screenshots, 24 Sep 2026): the login email first, the name cut off after it.
// Rulebook K3 / W10: pickers show names, never emails or IDs.
import { test } from "node:test"
import assert from "node:assert/strict"

import { approverOptions } from "../approverOptions.js"

test("the label is the person's name; the value stays the login", () => {
	assert.deepEqual(approverOptions([{ name: "hafiz@x.com", full_name: "Muhammad Nur Hafiz" }]), [
		{ label: "Muhammad Nur Hafiz", value: "hafiz@x.com" },
	])
})

test("two people with the same name are told apart by the part before the @", () => {
	const out = approverOptions([
		{ name: "ali.a@x.com", full_name: "Ali" },
		{ name: "ali.b@x.com", full_name: "Ali" },
	])
	assert.deepEqual(out.map((o) => o.label), ["Ali (ali.a)", "Ali (ali.b)"])
})

test("no full name falls back to the part before the @, never the whole address", () => {
	assert.equal(approverOptions([{ name: "hr.lead@x.com" }])[0].label, "hr.lead")
})

test("nothing in, nothing out", () => {
	assert.deepEqual(approverOptions(undefined), [])
})
