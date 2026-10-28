import assert from "node:assert/strict"
import { test } from "node:test"

import { teamPreview, awayCount, subline, chainRows } from "../orgChart.js"

test("teamPreview shows first n reports with overflow", () => {
	const reports = [
		{ id: "1", name: "Alice", designation: "Manager" },
		{ id: "2", name: "Bob", designation: "Developer" },
		{ id: "3", name: "Carol", designation: "Designer" },
		{ id: "4", name: "Dave", designation: "Developer" },
		{ id: "5", name: "Eve", designation: "Developer" },
		{ id: "6", name: "Frank", designation: "Analyst" },
	]
	const result = teamPreview(reports, 3)
	assert.deepEqual(result.shown, reports.slice(0, 3))
	assert.equal(result.more, 3)
})

test("teamPreview with fewer reports than n", () => {
	const reports = [
		{ id: "1", name: "Alice" },
		{ id: "2", name: "Bob" },
	]
	const result = teamPreview(reports, 5)
	assert.deepEqual(result.shown, reports)
	assert.equal(result.more, 0)
})

test("teamPreview with empty reports", () => {
	const result = teamPreview([], 5)
	assert.deepEqual(result.shown, [])
	assert.equal(result.more, 0)
})

test("awayCount returns number of away people", () => {
	const list = [
		{ id: "1", name: "Alice", away: true },
		{ id: "2", name: "Bob", away: false },
		{ id: "3", name: "Carol", away: true },
	]
	assert.equal(awayCount(list), 2)
})

test("awayCount with no away people", () => {
	const list = [
		{ id: "1", name: "Alice", away: false },
		{ id: "2", name: "Bob", away: false },
	]
	assert.equal(awayCount(list), 0)
})

test("awayCount with empty list", () => {
	assert.equal(awayCount([]), 0)
})

test("subline joins department and branch with no trailing dot", () => {
	const card = { department: "Operations", branch: "KL branch" }
	assert.equal(subline(card), "Operations · KL branch")
})

test("subline skips blank department", () => {
	const card = { department: "", branch: "KL branch" }
	assert.equal(subline(card), "KL branch")
})

test("subline skips blank branch", () => {
	const card = { department: "Operations", branch: "" }
	assert.equal(subline(card), "Operations")
})

test("subline skips both blanks", () => {
	const card = { department: "", branch: "" }
	assert.equal(subline(card), "")
})

test("chainRows maps left managers to a row", () => {
	const chain = [
		{ left: true, name: "Zulkifli Ahmad" },
		{ left: false, name: "Aminah Hassan", id: "r2" },
	]
	const result = chainRows(chain)
	assert.equal(result.length, 2)
	assert.equal(result[0].message, "Manager has left — HR to update")
	assert.equal(result[0].name, "Zulkifli Ahmad")
	assert.equal(result[1].name, "Aminah Hassan")
	assert.equal(result[1].message, undefined)
})

test("chainRows with all active managers", () => {
	const chain = [
		{ left: false, name: "Aminah Hassan", id: "r2" },
		{ left: false, name: "Rashid Ibrahim", id: "r1" },
	]
	const result = chainRows(chain)
	assert.equal(result.length, 2)
	result.forEach((r) => assert.equal(r.message, undefined))
})

test("chainRows with empty chain", () => {
	const result = chainRows([])
	assert.deepEqual(result, [])
})
