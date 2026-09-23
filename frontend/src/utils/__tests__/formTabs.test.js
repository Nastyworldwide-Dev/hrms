// A form's tabs are cut from the doctype's field list by each tab's LAST
// field. When that field is not in the list, the tab rendered EMPTY: on
// 22 Sep the expense form's allowlist dropped `taxes`, the one tab's
// `lastField`, and every new claim showed only "Attachments" and "Save"
// (audit FLOW-1 / P0-1). A missing boundary must never empty a tab.
import { test } from "node:test"
import assert from "node:assert/strict"

import { splitFieldsByTab } from "../formTabs.js"

const f = (...names) => names.map((fieldname) => ({ fieldname }))

test("each tab ends at its last field", () => {
	const out = splitFieldsByTab(f("a", "b", "c", "d"), [
		{ name: "One", lastField: "b" },
		{ name: "Two", lastField: "d" },
	])
	assert.deepEqual(
		out.One.map((x) => x.fieldname),
		["a", "b"]
	)
	assert.deepEqual(
		out.Two.map((x) => x.fieldname),
		["c", "d"]
	)
})

test("a tab whose last field is not in the list keeps every remaining field", () => {
	const out = splitFieldsByTab(f("expenses", "posting_date", "grand_total"), [
		{ name: "Expenses", lastField: "taxes" },
	])
	assert.deepEqual(
		out.Expenses.map((x) => x.fieldname),
		["expenses", "posting_date", "grand_total"]
	)
})

test("a missing boundary on a later tab does not swallow or repeat earlier fields", () => {
	const out = splitFieldsByTab(f("a", "b", "c"), [
		{ name: "One", lastField: "a" },
		{ name: "Two", lastField: "gone" },
	])
	assert.deepEqual(
		out.One.map((x) => x.fieldname),
		["a"]
	)
	assert.deepEqual(
		out.Two.map((x) => x.fieldname),
		["b", "c"]
	)
})

test("no tabs gives no groups", () => {
	assert.deepEqual(splitFieldsByTab(f("a"), undefined), {})
})

test("a missing boundary on a middle tab never empties the tabs after it", () => {
	const out = splitFieldsByTab(f("a", "b", "c", "d"), [
		{ name: "One", lastField: "a" },
		{ name: "Two", lastField: "gone" },
		{ name: "Three", lastField: "d" },
	])
	assert.deepEqual(
		out.Three.map((x) => x.fieldname),
		["b", "c", "d"]
	)
})

test("every field lands in exactly one tab, whatever the boundaries", () => {
	const fields = f("a", "b", "c", "d", "e")
	const shapes = [
		[
			{ name: "1", lastField: "x" },
			{ name: "2", lastField: "y" },
			{ name: "3", lastField: "z" },
		],
		[
			{ name: "1", lastField: "c" },
			{ name: "2", lastField: "a" },
			{ name: "3", lastField: "e" },
		],
		[
			{ name: "1", lastField: "b" },
			{ name: "2", lastField: "x" },
		],
	]
	for (const tabs of shapes) {
		const all = Object.values(splitFieldsByTab(fields, tabs)).flat()
		assert.deepEqual(
			all.map((x) => x.fieldname),
			["a", "b", "c", "d", "e"]
		)
	}
})
