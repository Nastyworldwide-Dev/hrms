// The All KPI tab has TWO resources and one set of chrome.
//
// `teamKpi` serves the manager tier, `departmentKpi` serves the tree tier, and
// `fetchTeam()` early-returns to `fetchTree()` for CEO/HR — so `teamKpi` is
// NEVER submitted for them. Any template binding left pointing at `teamKpi`
// therefore renders nothing at all for exactly the tier the feature was built
// for, silently: the hero was gated that way and the CEO's score, badge and
// ring simply disappeared, leaving controls, then tables, and no number.
//
// The rule this pins: shared chrome reads the SHARED payload — `teamData` for
// content and `teamResource` for loading/error — never a resource by name.
// `teamKpi` and `departmentKpi` may only appear where the tier is already
// known, i.e. in the computeds that choose between them.
//
// Run with: node --test "frontend/**/*.test.mjs"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { test } from "node:test"

const FILE = path.join(
	path.dirname(fileURLToPath(import.meta.url)),
	"..",
	"src",
	"views",
	"kpi",
	"Dashboard.vue"
)
const SOURCE = readFileSync(FILE, "utf8")
// Comments are prose — the rule is about BINDINGS. Stripping them keeps the
// guard honest instead of flagging the note that explains why it exists.
const TEMPLATE = SOURCE.slice(0, SOURCE.indexOf("<script setup>")).replace(
	/<!--[\s\S]*?-->/g,
	""
)

test("the template never binds a tier-specific resource directly", () => {
	const offenders = []
	for (const name of ["teamKpi", "departmentKpi"]) {
		for (const m of TEMPLATE.matchAll(new RegExp(`${name}\\.\\w+`, "g"))) {
			offenders.push(m[0])
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"shared chrome must read teamData / teamResource — a direct binding blanks " +
			`that block for whichever tier does not submit it. Found: ${offenders.join(
				", "
			)}`
	)
})

test("the shared payload computeds exist and choose on the tier", () => {
	for (const name of ["teamData", "teamResource"]) {
		assert.match(
			SOURCE,
			new RegExp(`const ${name} = computed\\(\\(\\) =>[^\\n]*isManagerTier`),
			`${name} must pick its source from the tier`
		)
	}
})

test("the hero is gated on the shared payload, not on one resource", () => {
	// The exact regression: `v-if="teamKpi.data && ..."` on the hero.
	const hero = TEMPLATE.slice(
		TEMPLATE.indexOf("teamSummary && teamSummary.headcount") - 900
	)
	assert.match(
		hero.slice(0, 900),
		/v-if="teamData &&/,
		"the hero must gate on teamData"
	)
})
