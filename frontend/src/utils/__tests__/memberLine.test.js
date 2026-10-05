// A member's second line on the Team page and the day sheet. HR can mark a DAY a half day
// (Attendance "Half Day", no leave filed): the chip stays Present because someone worked, but the
// boss read only "Present" and the half was lost (HR report, 5 Oct 2026: 2 Oct, Natrah).
import { test } from "node:test"
import assert from "node:assert/strict"
import { memberLine } from "../team.js"

const __ = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => String(args[i]))
const fmt = {
	punch: (t) => (t ? String(t).slice(11, 16) : "—"),
	time: (t) => String(t).slice(0, 5),
	day: (d) => d,
	shortDay: (d) => d,
}
const base = { status: "Present", first_in: null, last_out: null, half_day_marked: false }

test("a half day marked by HR says so after the punches", () => {
	const line = memberLine(
		{ ...base, first_in: "2026-10-02 12:38:00", half_day_marked: true },
		__,
		fmt
	)
	assert.equal(line, "IN 12:38 · OUT — · Half day")
})

test("a half day with no punches still says it, instead of a bare Present", () => {
	assert.equal(memberLine({ ...base, half_day_marked: true }, __, fmt), "Present · Half day")
})

test("a whole day is unchanged", () => {
	assert.equal(
		memberLine({ ...base, first_in: "2026-10-02 09:01:00", last_out: "2026-10-02 18:02:00" }, __, fmt),
		"IN 09:01 · OUT 18:02"
	)
	assert.equal(memberLine(base, __, fmt), "Present")
})

test("an approved half-day LEAVE keeps its own line", () => {
	const line = memberLine(
		{ ...base, status: "On Leave", leave_type: "Annual Leave", leave_until: "3 Oct", half_day_marked: true },
		__,
		fmt
	)
	assert.equal(line, "Annual Leave · until 3 Oct")
})
