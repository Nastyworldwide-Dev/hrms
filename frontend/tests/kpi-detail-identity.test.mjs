// The drill-down must render the person it NAMES.
//
// frappe-ui's createResource does not clear `.data` when a new submit starts
// (resources.js sets previousData/loading/error only), and `employeeKpi` is a
// module singleton. So on "open A -> back -> open B" a truthiness gate is still
// true and still holding A's payload: B's name renders above A's score, A's
// grade, A's ring, A's KRA targets and A's feedback count. Solid, no spinner,
// because the loading branch sits AFTER it and is unreachable once any payload
// exists. Somebody else's performance review, under the wrong name.
//
// The rule this pins: the detail is gated on WHO THE PAYLOAD IS ABOUT, taken
// from the payload itself, never on whether a payload exists.
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

/** The committed computed, executed rather than eyeballed. */
function buildGate() {
	const START = "const openedDetail = computed(() =>"
	const from = SOURCE.indexOf(START)
	assert.ok(
		from !== -1,
		"openedDetail was renamed or removed — the identity gate is gone"
	)
	const body = SOURCE.slice(from + START.length, SOURCE.indexOf("\n)", from))
	return (data, opened) =>
		new Function("employeeKpi", "openedEmployee", `return (${body})`)(
			{ data },
			{ value: opened }
		)
}

test("the payload for the person on screen renders", () => {
	const gate = buildGate()
	const payload = { employee: { name: "HR-EMP-B" } }
	assert.equal(gate(payload, "HR-EMP-B"), payload)
})

test("a previous person's payload does NOT render under a new name", () => {
	// The exact production shape: A still in the resource, B just opened.
	const gate = buildGate()
	assert.equal(gate({ employee: { name: "HR-EMP-A" } }, "HR-EMP-B"), null)
})

test("an empty resource renders nothing", () => {
	const gate = buildGate()
	assert.equal(gate(null, "HR-EMP-B"), null)
	assert.equal(gate(undefined, "HR-EMP-B"), null)
})

test("the loading branch is reachable — it is not stranded behind a truthy payload", () => {
	// The template must test the identity gate, not the raw resource. If this
	// regresses to `v-if="employeeKpi.data"` the loading state can never show
	// after the first drill-down, which is how the stale render hid.
	//
	// Two KpiDetail instances exist — My KPI and the drill-down. Only the
	// drill-down passes :heading, so that is the one this rule governs.
	const at = SOURCE.indexOf(":heading=")
	assert.ok(at !== -1, "the drill-down KpiDetail was renamed or removed")
	const open = SOURCE.lastIndexOf("<KpiDetail", at)
	const detail = SOURCE.slice(open, SOURCE.indexOf("/>", at) + 2)
	assert.match(
		detail,
		/v-if="openedDetail/,
		"the detail must gate on the identity-checked payload"
	)
	assert.doesNotMatch(
		detail,
		/v-if="employeeKpi\.data/,
		"gating on raw .data strands the loading branch"
	)
})
