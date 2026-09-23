// Team showed "Production - NW0A": the department's record name, company
// abbreviation and all (audit P2-2). People read a department by its own name.
// The record name stays the value (filters and links need it); only the words
// shown change.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { departmentLabel } from "../departmentLabel.js"

test("drops the company abbreviation ERPNext appends", () => {
	assert.equal(departmentLabel("Production - NW0A"), "Production")
	assert.equal(departmentLabel("Accounts - _TC"), "Accounts")
	assert.equal(departmentLabel("Research - and Development - NW0A"), "Research - and Development")
})

test("leaves a plain name, and nothing, alone", () => {
	assert.equal(departmentLabel("All Departments"), "All Departments")
	assert.equal(departmentLabel(""), "")
	assert.equal(departmentLabel(null), "")
})

test("every screen that prints a department goes through it", () => {
	const shown = {
		"../../views/team/TeamDashboard.vue": /departmentLabel\(group\.department\)/,
		"../../views/team/TeamRoster.vue": /member\.branch \|\| departmentLabel\(member\.department\)/,
		"../../views/issues/HRIssueBoard.vue": /departmentLabel\(issue\.department\)/,
		"../../views/sop/SopDetail.vue": /departmentLabel\(sop\.data\.department\)/,
		"../../views/sop/SopFormSheet.vue": /\{\{ departmentLabel\(department\.name\) \}\}/,
		"../../views/sop/SopList.vue": /departmentLabel\(section\.department\)/,
		"../../views/kpi/Dashboard.vue": /\{\{ departmentLabel\(d\) \}\}/,
	}
	for (const [file, pattern] of Object.entries(shown)) {
		const src = readFileSync(fileURLToPath(new URL(file, import.meta.url)), "utf8")
		assert.match(src, pattern, file)
	}
})
