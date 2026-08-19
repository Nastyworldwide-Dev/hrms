import test from "node:test"
import assert from "node:assert/strict"

import {
	buildManagerOptions,
	UNASSIGNED_DEPARTMENT,
} from "../src/utils/team.js"

const MANAGERS = [
	{
		name: "HR-EMP-1",
		employee_name: "Wan Natrah",
		department: "HR - NW",
		team_size: 5,
	},
	{
		name: "HR-EMP-2",
		employee_name: "Ahmad Taufik",
		department: "IT - NW",
		team_size: 3,
	},
	{
		name: "HR-EMP-3",
		employee_name: "Amran Shah",
		department: "HR - NW",
		team_size: 2,
	},
	{ name: "HR-EMP-4", employee_name: "Zed Nobody", team_size: 1 },
]

test("'My team' is pinned first with the empty value", () => {
	const options = buildManagerOptions(MANAGERS)
	assert.equal(options[0].items[0].label, "My team")
	assert.equal(options[0].items[0].value, "")
	assert.equal(options[0].hideLabel, true)
})

test("managers group by department, alphabetical, unassigned last", () => {
	const groups = buildManagerOptions(MANAGERS)
		.slice(1)
		.map((g) => g.group)
	assert.deepEqual(groups, ["HR - NW", "IT - NW", UNASSIGNED_DEPARTMENT])
})

test("options label as 'Name · team size' and carry the employee id", () => {
	const hr = buildManagerOptions(MANAGERS)[1]
	assert.deepEqual(hr.items, [
		{ label: "Wan Natrah · 5", value: "HR-EMP-1" },
		{ label: "Amran Shah · 2", value: "HR-EMP-3" },
	])
})

test("a manager without a count still gets a plain label", () => {
	const options = buildManagerOptions([{ name: "E", employee_name: "Solo" }])
	assert.equal(options[1].items[0].label, "Solo")
})

test("no managers means just the pinned My team", () => {
	const options = buildManagerOptions([])
	assert.equal(options.length, 1)
	assert.equal(options[0].items[0].value, "")
})
