// The Team page groups by department for DISPLAY; membership stays exactly
// the reports_to set the server returned. Run: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"

import { groupByDepartment, UNASSIGNED_DEPARTMENT } from "../src/utils/team.js"

const member = (name, department) => ({ employee: name, employee_name: name, department })

test("groups members under their department, sections alphabetical", () => {
	const groups = groupByDepartment([
		member("C", "Sales - WWSB"),
		member("A", "HR - WWSB"),
		member("B", "Sales - WWSB"),
	])
	assert.deepEqual(
		groups.map((g) => g.department),
		["HR - WWSB", "Sales - WWSB"]
	)
	assert.deepEqual(groups[1].members.map((m) => m.employee), ["C", "B"])
})

test("grouping never changes the member SET — presentation only", () => {
	const members = [member("A", "X"), member("B", null), member("C", "X"), member("D", "Y")]
	const regrouped = groupByDepartment(members).flatMap((g) => g.members)
	assert.equal(regrouped.length, members.length)
	assert.deepEqual(new Set(regrouped.map((m) => m.employee)), new Set(["A", "B", "C", "D"]))
})

test("members without a department gather under the labelled bucket, last", () => {
	const groups = groupByDepartment([member("A", null), member("B", "Ops")])
	assert.deepEqual(
		groups.map((g) => g.department),
		["Ops", UNASSIGNED_DEPARTMENT]
	)
})

test("empty and missing input stay harmless", () => {
	assert.deepEqual(groupByDepartment([]), [])
	assert.deepEqual(groupByDepartment(undefined), [])
})
