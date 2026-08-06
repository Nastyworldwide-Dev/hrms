// Tests for the HR Issue Board's pure filter/count logic (v15.105.0).
// The board filters client-side (status tabs, type filter, search); these
// keep that logic honest. Run with: node --test frontend/tests/*.test.mjs
import { test } from "node:test"
import assert from "node:assert/strict"

import { countByStatus, filterIssues } from "../src/utils/issueBoard.js"

const ISSUES = [
	{
		name: "HR-ISS-26-08-00001",
		employee_name: "Aisyah Rahman",
		department: "Retail Ops",
		issue_type: "Leave Balance Discrepancy",
		urgency: "High",
		status: "Open",
		details: "Annual leave balance wrong",
	},
	{
		name: "HR-ISS-26-08-00002",
		employee_name: "Danish Lim",
		department: "Warehouse",
		issue_type: "Check-in / Check-out Problem",
		urgency: "Medium",
		status: "Open",
		details: "Check-out did not register",
	},
	{
		name: "HR-ISS-26-08-00003",
		employee_name: "Priya Nair",
		department: "Finance",
		issue_type: "Other HR Issue",
		urgency: "High",
		status: "In Progress",
		details: "Bank account update",
	},
	{
		name: "HR-ISS-26-07-00009",
		employee_name: "Aisyah Rahman",
		department: "Retail Ops",
		issue_type: "Check-in / Check-out Problem",
		urgency: "High",
		status: "Completed",
		details: "Missing OUT punch",
	},
]

test("status tab filters to that status only", () => {
	const open = filterIssues(ISSUES, { status: "Open" })
	assert.deepEqual(
		open.map((issue) => issue.name),
		["HR-ISS-26-08-00001", "HR-ISS-26-08-00002"]
	)
})

test("type filter and status compose", () => {
	const rows = filterIssues(ISSUES, {
		status: "Open",
		issueType: "Check-in / Check-out Problem",
	})
	assert.deepEqual(
		rows.map((issue) => issue.name),
		["HR-ISS-26-08-00002"]
	)
})

test("search matches name, employee, department, and details, case-insensitive", () => {
	assert.equal(filterIssues(ISSUES, { search: "aisyah" }).length, 2)
	assert.equal(filterIssues(ISSUES, { search: "FINANCE" }).length, 1)
	assert.equal(filterIssues(ISSUES, { search: "26-07-00009" }).length, 1)
	assert.equal(filterIssues(ISSUES, { search: "did not register" }).length, 1)
	assert.equal(filterIssues(ISSUES, { search: "no-such-thing" }).length, 0)
})

test("empty filters return everything; empty input returns empty", () => {
	assert.equal(filterIssues(ISSUES, {}).length, 4)
	assert.equal(filterIssues(ISSUES).length, 4)
	assert.deepEqual(filterIssues(undefined, { status: "Open" }), [])
})

test("countByStatus tallies statuses and open high-urgency", () => {
	const counts = countByStatus(ISSUES)
	assert.equal(counts["Open"], 2)
	assert.equal(counts["In Progress"], 1)
	assert.equal(counts["Completed"], 1)
	// high urgency counts only unresolved tickets — the Completed one is excluded
	assert.equal(counts.high, 2)
})

test("countByStatus handles empty input", () => {
	assert.deepEqual(countByStatus([]), {
		Open: 0,
		"In Progress": 0,
		Completed: 0,
		high: 0,
	})
})
