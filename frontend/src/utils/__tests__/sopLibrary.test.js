// Tests for the SOP Library's pure search/grouping logic (v15.106.0).
// The list filters the get_sops payload client-side (search box across
// Essentials + General + department groups); these keep that logic honest.
// Run with: node --test frontend/tests/*.test.mjs
import { test } from "node:test"
import assert from "node:assert/strict"

import {
	buildSopSections,
	filterSops,
	matchesQuery,
} from "../sopLibrary.js"

const PAYLOAD = {
	is_hr: true,
	my_department: "Kitchen - NW",
	pinned: [
		{ name: "HR-SOP-00001", title: "Employee Handbook", scope: "General" },
	],
	general: [
		{
			name: "HR-SOP-00002",
			title: "Fire Evacuation Procedure",
			scope: "General",
		},
		{ name: "HR-SOP-00003", title: "IT Acceptable Use", scope: "General" },
	],
	departments: [
		{
			department: "Kitchen - NW",
			sops: [{ name: "HR-SOP-00004", title: "Kitchen Opening Checklist" }],
		},
		{
			department: "Service - NW",
			sops: [{ name: "HR-SOP-00005", title: "Guest Greeting Standard" }],
		},
	],
}

test("matchesQuery is case-insensitive and passes everything on an empty query", () => {
	assert.equal(matchesQuery("Fire Evacuation Procedure", "fire"), true)
	assert.equal(matchesQuery("Fire Evacuation Procedure", "  EVACUATION "), true)
	assert.equal(matchesQuery("Fire Evacuation Procedure", "payroll"), false)
	assert.equal(matchesQuery("Anything", ""), true)
	assert.equal(matchesQuery(undefined, "fire"), false)
})

test("filterSops tolerates a missing list", () => {
	assert.deepEqual(filterSops(undefined, "fire"), [])
	assert.equal(filterSops(PAYLOAD.general, "").length, 2)
})

test("buildSopSections groups General first, then each department", () => {
	const { pinned, sections, isEmpty } = buildSopSections(PAYLOAD, "")
	assert.equal(isEmpty, false)
	assert.equal(pinned.length, 1)
	assert.deepEqual(
		sections.map((s) => s.department),
		[null, "Kitchen - NW", "Service - NW"]
	)
	assert.equal(sections[0].key, "general")
	assert.equal(sections[1].sops[0].title, "Kitchen Opening Checklist")
})

test("buildSopSections drops groups with no match so no bare header renders", () => {
	const { pinned, sections } = buildSopSections(PAYLOAD, "kitchen")
	assert.equal(pinned.length, 0)
	assert.equal(sections.length, 1)
	assert.equal(sections[0].department, "Kitchen - NW")
})

test("buildSopSections reports empty only when nothing matches at all", () => {
	assert.equal(buildSopSections(PAYLOAD, "handbook").isEmpty, false)
	assert.equal(buildSopSections(PAYLOAD, "zzz").isEmpty, true)
	assert.equal(buildSopSections(undefined, "").isEmpty, true)
})

// SOP folders (owner, 27 Oct 2026): folders list only what this reader sees
// in them; search stays flat, each hit naming its folder.
const FOLDERED = {
	...PAYLOAD,
	pinned: [
		{ name: "HR-SOP-00001", title: "Employee Handbook", scope: "General", folder: "Safety" },
	],
	folders: [
		{
			name: "Safety",
			folder_name: "Safety",
			count: 2,
			sops: [
				{ name: "HR-SOP-00001", title: "Employee Handbook", folder: "Safety" },
				{ name: "HR-SOP-00006", title: "Fire Drill", folder: "Safety" },
			],
		},
		{ name: "Empty", folder_name: "Empty", count: 0, sops: [] },
	],
}

test("buildSopSections lists folders with SOPs in them, not empty ones", () => {
	const { folders } = buildSopSections(FOLDERED, "")
	assert.deepEqual(
		folders.map((f) => [f.name, f.count]),
		[["Safety", 2]]
	)
})

test("a search is one flat list, each hit naming its folder, no duplicates", () => {
	const { folders, results, isEmpty } = buildSopSections(FOLDERED, "fire")
	assert.equal(folders.length, 0)
	assert.equal(isEmpty, false)
	assert.deepEqual(
		results.map((r) => [r.title, r.folderName]),
		[
			["Fire Drill", "Safety"],
			["Fire Evacuation Procedure", null],
		]
	)
	const handbook = buildSopSections(FOLDERED, "handbook").results
	assert.equal(handbook.length, 1)
	assert.equal(handbook[0].folderName, "Safety")
})

test("without a search there are no flat results", () => {
	assert.deepEqual(buildSopSections(FOLDERED, "").results, [])
})

test("a search that only finds a filed SOP is not empty", () => {
	const { results, isEmpty } = buildSopSections(FOLDERED, "drill")
	assert.equal(results.length, 1)
	assert.equal(isEmpty, false)
})
