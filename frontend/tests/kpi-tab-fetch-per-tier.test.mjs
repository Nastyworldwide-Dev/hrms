// The KPI team tab must FETCH for every tier that can see it.
//
// The tab's label became per-tier ("Team KPI" for a manager, "All KPI" for the
// CEO and HR) while the first-fetch watch still compared the active tab against
// the literal TEAM constant. For the CEO and HR that comparison never matched,
// so fetchTeam() was never called — and there is no other trigger: it is
// otherwise reachable only from the filter bar, which itself renders only once
// a fetch has returned. The tab was permanently "No appraisals here", for the
// two tiers the feature exists to serve.
//
// The rule this pins: the trigger keys on the tab's IDENTITY (not MINE), never
// on a label. Labels are presentation and will change again.
//
// Run with: node --test "frontend/**/*.test.mjs"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { test } from "node:test"

const SOURCE = readFileSync(
	path.join(
		path.dirname(fileURLToPath(import.meta.url)),
		"..",
		"src",
		"views",
		"kpi",
		"Dashboard.vue"
	),
	"utf8"
)

/** The labels the component itself declares, read from source so a rename
 *  cannot leave this test asserting a string the app no longer uses. */
function labels() {
	const grab = (name) => {
		const m = new RegExp(`const ${name} = "([^"]+)"`).exec(SOURCE)
		assert.ok(m, `constant not found in the component: ${name}`)
		return m[1]
	}
	return { MINE: grab("MINE"), TEAM: grab("TEAM"), ALL: grab("ALL") }
}

/** The committed watch body, executed rather than eyeballed. */
function buildTrigger({ MINE }) {
	const START = "watch(activeTab, (tab) => {"
	const from = SOURCE.indexOf(START)
	assert.ok(from !== -1, "the first-fetch watch was renamed or removed")
	const body = SOURCE.slice(from + START.length, SOURCE.indexOf("})", from))
	let fetched = false
	// Every name the watch body reaches for is injected. A new dependency in
	// that body fails HERE rather than silently — which is the point of running
	// the committed source instead of a copy of it.
	const fn = new Function(
		"tab",
		"MINE",
		"teamData",
		"teamResource",
		"fetchTeam",
		"closeEmployee",
		`${body}; return null`
	)
	return (tab) => {
		fetched = false
		fn(
			tab,
			MINE,
			{ value: null },
			{ value: { loading: false } },
			() => {
				fetched = true
			},
			() => {}
		)
		return fetched
	}
}

test("every tier's team tab triggers the first fetch", () => {
	const L = labels()
	const trigger = buildTrigger(L)
	for (const [tier, label] of [
		["manager", L.TEAM],
		["ceo", L.ALL],
		["hr", L.ALL],
	]) {
		assert.ok(
			trigger(label),
			`tab "${label}" (${tier}) did not trigger fetchTeam()`
		)
	}
})

test("the My KPI tab never triggers a team fetch", () => {
	const L = labels()
	assert.equal(buildTrigger(L)(L.MINE), false)
})

test("the trigger does not compare against a label constant", () => {
	// A label comparison is what broke it. Keying on identity survives the next
	// rename; keying on TEAM or ALL does not.
	const START = "watch(activeTab, (tab) => {"
	const from = SOURCE.indexOf(START)
	const body = SOURCE.slice(from, SOURCE.indexOf("})", from))
	assert.doesNotMatch(body, /===\s*TEAM\b/, "trigger keys on the TEAM label")
	assert.doesNotMatch(body, /===\s*ALL\b/, "trigger keys on the ALL label")
})
