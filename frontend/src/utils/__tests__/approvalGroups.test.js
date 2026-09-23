// The grouped Approvals page (owner-approved design, 23 Sep 2026).
//
//   Waiting on you · 23
//   YOURS
//     Production · 8
//       Time off · 2
//       Overtime · 6
//   OTHER TEAMS
//     QC · Ahmad Faiz's team · 5
//
// The server says where each row belongs (section, department, approver_name);
// this module only groups what it was given, oldest first, one line per person
// per kind. It never drops or adds a row.
import { test } from "node:test"
import assert from "node:assert/strict"

import { groupApprovals, pageOf, personLine, GROUP_PREVIEW, PAGE_SIZE } from "../approvalGroups.js"

const t = (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])

const row = (name, over = {}) => ({
	doctype: "OT Request",
	name,
	kind: "Overtime",
	employee: "E1",
	who: "Mohd Shazwan",
	hours: 0,
	section: "yours",
	department: "Production",
	approver_name: "",
	modified: name,
	...over,
})

test("rows split into yours and other teams, each counted", () => {
	const g = groupApprovals([
		row("1"),
		row("2", { section: "other", department: "QC", approver_name: "Ahmad Faiz" }),
		row("3", { kind: "Time off", doctype: "Leave Application" }),
	])
	assert.equal(g.total, 3)
	assert.equal(g.yours.count, 2)
	assert.equal(g.other.count, 1)
})

test("yours groups by department, then by kind", () => {
	const g = groupApprovals([
		row("1"),
		row("2", { kind: "Time off", doctype: "Leave Application", employee: "E2", who: "Aisyah" }),
		row("3", { department: "Warehouse" }),
	])
	assert.deepEqual(
		g.yours.departments.map((d) => [d.name, d.count, d.kinds.map((k) => [k.kind, k.count])]),
		[
			["Production", 2, [["Overtime", 1], ["Time off", 1]]],
			["Warehouse", 1, [["Overtime", 1]]],
		]
	)
})

test("other teams are one group per department and direct approver", () => {
	const other = { section: "other" }
	const g = groupApprovals([
		row("1", { ...other, department: "QC", approver_name: "Ahmad Faiz" }),
		row("2", { ...other, department: "Logistics", approver_name: "Siti Aminah" }),
		row("3", { ...other, department: "QC", approver_name: "Ahmad Faiz", employee: "E9" }),
	])
	assert.deepEqual(
		g.other.teams.map((team) => [team.name, team.approverName, team.count, team.people.length]),
		[
			["QC", "Ahmad Faiz", 2, 2],
			["Logistics", "Siti Aminah", 1, 1],
		]
	)
})

test("one line per person per kind: requests counted, overtime hours summed", () => {
	const g = groupApprovals([
		row("1", { hours: 8 }),
		row("2", { hours: 6.5 }),
		row("3", { hours: 0 }),
		row("4", { employee: "E2", who: "Aisyah", hours: 1 }),
	])
	const people = g.yours.departments[0].kinds[0].people
	assert.equal(people.length, 2)
	assert.equal(people[0].count, 3)
	assert.equal(people[0].hours, 14.5)
	assert.deepEqual(
		people[0].rows.map((r) => r.name),
		["1", "2", "3"],
		"the person's own requests, oldest first"
	)
	assert.equal(personLine(people[0], t), "Mohd Shazwan · 3 days · 14h 30m")
})

test("other kinds say how many requests", () => {
	const g = groupApprovals([
		row("1", { kind: "Time off", doctype: "Leave Application" }),
		row("2", { kind: "Time off", doctype: "Leave Application" }),
	])
	assert.equal(personLine(g.yours.departments[0].kinds[0].people[0], t), "Mohd Shazwan · 2 requests")
})

test("one of anything is singular", () => {
	const g = groupApprovals([row("1", { hours: 0.5 })])
	assert.equal(personLine(g.yours.departments[0].kinds[0].people[0], t), "Mohd Shazwan · 1 day · 30m")
})

test("oldest first: a group is placed by its oldest request", () => {
	const g = groupApprovals([
		row("2026-09-10", { department: "Warehouse" }),
		row("2026-09-11"),
		row("2026-09-01", { department: "Production", employee: "E2" }),
	])
	assert.deepEqual(
		g.yours.departments.map((d) => d.name),
		["Production", "Warehouse"]
	)
})

test("a row with no department still shows", () => {
	const g = groupApprovals([row("1", { department: "" })])
	assert.equal(g.yours.departments[0].name, "")
	assert.equal(g.yours.count, 1)
})

test("five lines, then See all; expanded pages twenty at a time", () => {
	const people = Array.from({ length: 47 }, (_, i) => ({ key: String(i) }))
	assert.equal(GROUP_PREVIEW, 5)
	assert.equal(PAGE_SIZE, 20)
	const closed = pageOf(people, { expanded: false, pages: 1 })
	assert.equal(closed.rows.length, 5)
	assert.equal(closed.seeAll, true)
	assert.equal(closed.left, 0)
	const open = pageOf(people, { expanded: true, pages: 1 })
	assert.equal(open.rows.length, 20)
	assert.equal(open.seeAll, false)
	assert.equal(open.left, 27)
	assert.equal(pageOf(people, { expanded: true, pages: 3 }).left, 0)
})

test("a short group has no See all", () => {
	const view = pageOf([{ key: "a" }, { key: "b" }], { expanded: false, pages: 1 })
	assert.equal(view.seeAll, false)
	assert.equal(view.rows.length, 2)
})

test("other teams start collapsed when they hold more than five lines", () => {
	const other = (i) => row(String(i), { section: "other", employee: `E${i}`, department: "QC" })
	assert.equal(groupApprovals([1, 2, 3, 4, 5].map(other)).other.startCollapsed, false)
	assert.equal(groupApprovals([1, 2, 3, 4, 5, 6].map(other)).other.startCollapsed, true)
})
