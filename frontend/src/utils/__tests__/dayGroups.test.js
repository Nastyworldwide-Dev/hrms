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
