// Class guard: a "Team …" tab must never be shown unconditionally.
//
// The recurring bug — a hardcoded TAB_BUTTONS array with a "Team X" entry —
// gave every plain employee a permanently empty (or inappropriate) Team tab.
// RequestPanel fixed it by gating on isApprover; the leave / expense / shift
// list views each shipped the same hardcoded array with no gate. This scans
// every view for a TAB_BUTTONS that names a Team tab and fails if that file
// doesn't reference isApprover — so the next hardcoded team tab fails the build
// instead of leaking to a non-manager.

import assert from "node:assert/strict"
import { readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { test } from "node:test"

const VIEWS = path.join(
	path.dirname(fileURLToPath(import.meta.url)),
	"..",
	"src"
)

function walk(dir) {
	const out = []
	for (const e of readdirSync(dir, { withFileTypes: true })) {
		const p = path.join(dir, e.name)
		if (e.isDirectory()) out.push(...walk(p))
		else if (e.name.endsWith(".vue")) out.push(p)
	}
	return out
}

// The guard names the GATES, not one predicate. It began as `isApprover` alone,
// which failed kpi/Dashboard.vue the day that view shipped a Team tab behind
// `canViewTeamKpi` — a STRICTER gate. A class guard that is red for a correct
// file gets ignored, and an ignored guard is how the next genuinely ungated
// Team tab gets in. Add a gate here when you add one; never widen this to a
// bare "has any v-if".
const TEAM_TAB_GATES = ["isApprover", "canViewTeamKpi", "hasTeam"]

test("every view with a Team tab gates it on a known gate", () => {
	const offenders = []
	for (const file of walk(VIEWS)) {
		const src = readFileSync(file, "utf8")
		// a TAB_BUTTONS (or tabButtons) declaration that names a "Team …" tab
		const declaresTeamTab = /TAB_BUTTONS[\s\S]{0,200}?["']Team /.test(src)
		if (declaresTeamTab && !TEAM_TAB_GATES.some((gate) => src.includes(gate))) {
			offenders.push(path.relative(VIEWS, file))
		}
	}
	assert.deepEqual(
		offenders,
		[],
		`these views show a Team tab with none of ${TEAM_TAB_GATES.join(
			" / "
		)}: ${offenders.join(", ")}`
	)
})
