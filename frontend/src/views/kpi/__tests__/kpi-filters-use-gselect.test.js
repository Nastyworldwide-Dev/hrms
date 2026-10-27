// Design audit, 27 Oct 2026: the KPI Dashboard drew its six filters as raw <select>s with a local
// .kpi-filter skin (square corners, 13 px, its own border) next to Glass pickers everywhere else.
// GSelect is the one picker (native wheel on iPhone, 44 px, two-tone focus ring). The handlers
// still run on every change, after the value is set.
// Run: cd frontend && node --test src/views/kpi/__tests__/kpi-filters-use-gselect.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Dashboard.vue", import.meta.url)), "utf8")
const template = src.slice(0, src.indexOf("<script"))

test("no raw select and no local filter skin", () => {
	assert.doesNotMatch(template, /<select\b/)
	assert.doesNotMatch(src, /\.kpi-filter\b/)
})

test("each filter is a GSelect that still calls its handler", () => {
	for (const [model, handler] of [
		["selectedYear", "onYearChange"],
		["selectedCycle", "refetch"],
		["teamYear", "onTeamYearChange"],
		["teamCycle", "fetchTeam"],
		["teamCompany", "onTeamCompanyChange"],
		["teamDepartment", "fetchTeam"],
	])
	{
		const tag = [...template.matchAll(/<GSelect\b[\s\S]*?\/>/g)].map((m) => m[0]).find((t) => t.includes(`v-model="${model}"`))
		assert.ok(tag, model)
		assert.match(tag, new RegExp(`@update:model-value="${handler}"`), model)
	}
})
