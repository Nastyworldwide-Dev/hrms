// The Calendar day sheet's team, grouped by status (owner, 28 Sep 2026: "team
// ... must be shown at calendar page, alongside the roster"). Everyone, once
// (owner, 29 Sep 2026, after Hafiz's report: the sheet said 6 and listed 5,
// and showed the team three times over).
import assert from "node:assert/strict"
import { test } from "node:test"

import { dayTeamGroups } from "../dayTeamGroups.js"

const row = (employee, status) => ({ employee, employee_name: employee, status })

test("groups follow a fixed order, and only non-empty groups show", () => {
	const groups = dayTeamGroups([
		row("A", "On Leave"),
		row("B", "Present"),
		row("C", "Not In Yet"),
		row("D", "Present"),
	])
	assert.deepEqual(
		groups.map((g) => [g.status, g.members.map((m) => m.employee)]),
		[
			["Present", ["B", "D"]],
			["Not In Yet", ["C"]],
			["On Leave", ["A"]],
		]
	)
})

test("a status the sheet does not know still shows, last", () => {
	const groups = dayTeamGroups([row("A", "Scheduled"), row("B", "Present")])
	assert.deepEqual(
		groups.map((g) => g.status),
		["Present", "Scheduled"]
	)
})

test("no member is ever added, dropped or duplicated", () => {
	const rows = ["Present", "Absent", "Off", "Not In Yet", "On Leave", "Scheduled"].map((s, i) =>
		row(`E${i}`, s)
	)
	const out = dayTeamGroups(rows).flatMap((g) => g.members.map((m) => m.employee))
	assert.deepEqual(out.sort(), rows.map((r) => r.employee).sort())
})

test("Hafiz's team of six: every heading number is the names under it", () => {
	const team = ["A", "B", "C", "D"].map((e) => row(e, "Present"))
	team.push(row("E", "Not In Yet"), row("F", "Not In Yet"))
	const groups = dayTeamGroups(team)
	assert.deepEqual(
		groups.map((g) => [g.status, g.members.length]),
		[
			["Present", 4],
			["Not In Yet", 2],
		],
		"Not in yet (2) lists both names"
	)
})

test("nothing in, nothing out", () => {
	assert.deepEqual(dayTeamGroups(undefined), [])
	assert.deepEqual(dayTeamGroups([]), [])
})
