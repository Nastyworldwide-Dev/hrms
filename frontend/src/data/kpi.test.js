// Team KPI is a READ-ONLY view of every employee's appraisal score, offered to
// one person. Two properties have to stay true of this module, and neither is
// visible from the rendered page — a regression in either is silent:
//
//   1. it declares no write endpoint. The day someone adds `update_score` here
//      the CEO's read-only view becomes an editing surface for the whole
//      company, and nothing on screen would say so.
//   2. the designation gate is cached PER USER. `createResource({cache: "..."})`
//      with a bare string key is shared across sessions in the same browser
//      profile, so a shared or handover device would serve the CEO's "yes" to
//      the next person to sign in. personalCacheKey is what prevents that.
//
// This reads the module source rather than importing it: the module resolves
// "@/utils/personalCache", a Vite alias node's resolver knows nothing about.
// The assertions are therefore structural on purpose, and they are the two
// structural facts that carry the security of the feature.
//
// Run with: node --test "frontend/**/*.test.js"
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(fileURLToPath(new URL("./kpi.js", import.meta.url)), "utf8")

/** Every `url: "..."` declared in the module, in source order. */
const declaredUrls = [...source.matchAll(/url:\s*"([^"]+)"/g)].map((m) => m[1])

// The only endpoints this view is allowed to reach. Every one is a READ, and
// every one re-checks the caller's tier server-side. Adding a line here is a
// deliberate act: say what the endpoint reads and what fences it.
const READ_ONLY_ENDPOINTS = [
	// the tier gate — returns "manager" | "ceo" | "hr" | nothing
	"hrms.api.kpi.can_view_team_kpi",
	// the list — rows the caller's tier admits
	"hrms.api.kpi.get_team_kpi",
	// one person's KRA detail. The only KPI endpoint that takes an employee,
	// so the only one whose safety is by CHECK rather than by construction:
	// _require_kpi_read runs before a row is read.
	"hrms.api.kpi.get_employee_kpi",
]

test("declares both Team KPI endpoints", () => {
	for (const endpoint of READ_ONLY_ENDPOINTS) {
		assert.ok(declaredUrls.includes(endpoint), `missing resource for ${endpoint}`)
	}
})

test("declares no endpoint outside the read-only pair", () => {
	const extra = declaredUrls.filter((url) => !READ_ONLY_ENDPOINTS.includes(url))
	assert.deepEqual(
		extra,
		[],
		`Team KPI is read-only; remove ${extra.join(", ")} or move it out of data/kpi.js`
	)
})

test("the designation gate is cached per user, never under a shared key", () => {
	const gate = source.slice(source.indexOf("canViewTeamKpi"))
	const cacheLine = /cache:\s*(.+)/.exec(gate)
	assert.ok(cacheLine, "canViewTeamKpi must declare a cache key")
	assert.match(
		cacheLine[1],
		/personalCacheKey\(/,
		"a bare cache key is shared between sessions in one browser profile"
	)
})
