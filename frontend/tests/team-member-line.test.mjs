// One member's second line, shared by the Team page and the Calendar day sheet
// so the two screens describe a person in the same words (28 Sep 2026).
import { test } from "node:test"
import assert from "node:assert/strict"

import { memberLine } from "../src/utils/team.js"

const __ = (text, args) =>
	args ? text.replace(/\{(\d)\}/g, (_, i) => args[i]) : text
const fmt = {
	punch: (v) => (v ? v.slice(11, 16) : "—"),
	time: (v) => (v ? v.slice(0, 5) : "—"),
	day: (v) => `D(${v})`,
	shortDay: (v) => `S(${v})`,
}

test("in and out times for someone who punched", () => {
	const line = memberLine(
		{ status: "Present", first_in: "2026-09-28 09:02:00", last_out: null },
		__,
		fmt
	)
	assert.equal(line, "IN 09:02 · OUT —")
})

test("a check-out after midnight says next day", () => {
	const line = memberLine(
		{
			status: "Present",
			first_in: "2026-09-28 09:00:00",
			last_out: "2026-09-29 01:41:00",
			out_next_day: true,
		},
		__,
		fmt
	)
	assert.equal(line, "IN 09:00 · OUT 01:41 (next day)")
})

test("leave shows the type and until when, never a reason", () => {
	const line = memberLine(
		{
			status: "On Leave",
			leave_type: "Annual Leave",
			leave_until: "2026-09-30",
		},
		__,
		fmt
	)
	assert.equal(line, "Annual Leave · until S(2026-09-30)")
})

test("not in yet names the shift", () => {
	const line = memberLine(
		{ status: "Not In Yet", shift_start: "09:00:00", shift_end: "18:00:00" },
		__,
		fmt
	)
	assert.equal(line, "Shift 09:00–18:00 · no punch yet")
})

test("absent says there is nothing on file", () => {
	assert.equal(
		memberLine({ status: "Absent" }, __, fmt),
		"No punch · no leave filed"
	)
})

test("worked past midnight says where it counted", () => {
	assert.equal(
		memberLine({ status: "Present", counted_on: "2026-09-27" }, __, fmt),
		"Worked past midnight · counted on D(2026-09-27)"
	)
})
