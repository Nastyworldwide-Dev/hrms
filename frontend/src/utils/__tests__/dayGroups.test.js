// alpha.7 0.8: the check-ins list repeated the day on every row ("Today",
// "Today", "Today"). iOS lists group by day under a header instead.
import { test } from "node:test"
import assert from "node:assert/strict"
import { groupByDay, dayHeading } from "../dayGroups.js"

test("rows keep their order and fall under one heading per day", () => {
	const rows = [
		{ name: "a", day: "2026-09-24" },
		{ name: "b", day: "2026-09-24" },
		{ name: "c", day: "2026-09-22" },
	]
	const groups = groupByDay(rows, (r) => r.day)
	assert.deepEqual(
		groups.map((g) => [g.day, g.rows.map((r) => r.name)]),
		[
			["2026-09-24", ["a", "b"]],
			["2026-09-22", ["c"]],
		]
	)
})

test("a day that comes back later in the list is not merged across the gap", () => {
	// The list is server-ordered; regrouping would reorder punches.
	const groups = groupByDay([{ d: "x" }, { d: "y" }, { d: "x" }], (r) => r.d)
	assert.equal(groups.length, 3)
})

test("headings: Today, Yesterday, weekday + date, year only when not this year", () => {
	const today = "2026-09-24"
	assert.equal(dayHeading("2026-09-24", today), "Today")
	assert.equal(dayHeading("2026-09-23", today), "Yesterday")
	assert.equal(dayHeading("2026-09-22", today), "Tue 22 Sep")
	assert.equal(dayHeading("2025-12-31", today), "Wed 31 Dec 2025")
})

// alpha.11, the one work-day rule (owner, 26 Sep 2026): a check-out after
// midnight belongs to the day its session started. The check-ins list put a
// 01:41 check-out alone under the next day, like a day nobody checked out of.
import { workDayOf } from "../dayGroups.js"

test("a check-out after midnight is grouped with the day it closes", () => {
	const rows = [
		{ name: "out", log_type: "OUT", time: "2026-09-26 01:41:00" },
		{ name: "in", log_type: "IN", time: "2026-09-25 22:45:00" },
	]
	const dayOf = workDayOf(rows)
	assert.deepEqual(groupByDay(rows, dayOf).map((g) => [g.day, g.rows.map((r) => r.name)]), [
		["2026-09-25", ["out", "in"]],
	])
})

test("a tap stamped with a shift uses the shift's day", () => {
	const rows = [{ name: "out", log_type: "OUT", time: "2026-09-26 01:41:00", shift_start: "2026-09-25 21:00:00" }]
	assert.equal(workDayOf(rows)(rows[0]), "2026-09-25")
})

test("the next morning's check-in is its own day", () => {
	const rows = [
		{ name: "in2", log_type: "IN", time: "2026-09-26 08:30:00" },
		{ name: "out", log_type: "OUT", time: "2026-09-25 18:00:00" },
		{ name: "in", log_type: "IN", time: "2026-09-25 09:00:00" },
	]
	const dayOf = workDayOf(rows)
	assert.deepEqual(rows.map(dayOf), ["2026-09-26", "2026-09-25", "2026-09-25"])
})
