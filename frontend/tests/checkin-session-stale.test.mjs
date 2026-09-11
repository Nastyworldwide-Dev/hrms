// A forgotten check-out from an EARLIER day must not make today's fresh
// check-in look stale. Nabil, 10 Sep: "my check in status in nadi pwa still
// ask for check in despite i already checked in."
// Run: node --test frontend/tests/checkin-session-stale.test.mjs
import test from "node:test"
import assert from "node:assert"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const HERE = path.dirname(fileURLToPath(import.meta.url))
const SOURCE = readFileSync(
	path.join(HERE, "..", "src", "components", "CheckInPanel.vue"),
	"utf8"
)

// The rule, lifted verbatim from the component so the test drives the real
// logic rather than a copy that can drift.
function buildRule(staleData) {
	// Both anchors are ASSERTED, not assumed. Slicing on indexOf("...") returns
	// -1 for a missing anchor, which silently takes the slice to the end of the
	// file (or the start) and breaks four tests with an unrelated-looking error.
	// That is exactly what happened when `nextAction` was renamed `liveAction`.
	const START = "function isSessionStale(log) {"
	const END = "const liveAction = computed"
	const from = SOURCE.indexOf(START)
	const to = SOURCE.indexOf(END)
	assert.ok(from !== -1, `anchor not found in the component: ${START}`)
	assert.ok(to > from, `anchor not found after the rule: ${END}`)
	const body = SOURCE.slice(from, to)
	// Parsed, never hardcoded: injecting a literal let the ceiling test pass
	// unchanged when the component's ceiling was set to 4.
	const MAX_OPEN_SHIFT_HOURS = Number(
		SOURCE.match(/const MAX_OPEN_SHIFT_HOURS = (\d+)/)?.[1]
	)
	assert.ok(MAX_OPEN_SHIFT_HOURS, "ceiling constant not found in the component")
	const unresolvedStaleIn = { data: staleData }
	return new Function(
		"MAX_OPEN_SHIFT_HOURS",
		"unresolvedStaleIn",
		`${body}; return isSessionStale`
	)(MAX_OPEN_SHIFT_HOURS, unresolvedStaleIn)
}

function minutesAgo(n) {
	const d = new Date(Date.now() - n * 60000)
	const pad = (x) => String(x).padStart(2, "0")
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
		d.getHours()
	)}:${pad(d.getMinutes())}:00`
}

test("an abandoned IN from an earlier day does not make today's check-in stale", () => {
	const isSessionStale = buildRule({
		name: "CKIN-OLD",
		time: "2026-09-07 09:00:00",
		is_abandoned: 1,
	})
	const today = { name: "CKIN-TODAY", time: minutesAgo(30), log_type: "IN" }
	assert.strictEqual(isSessionStale(today), false)
})

test("the abandoned session itself is still stale", () => {
	const isSessionStale = buildRule({
		name: "CKIN-OLD",
		time: minutesAgo(30),
		is_abandoned: 1,
	})
	const old = { name: "CKIN-OLD", time: minutesAgo(30), log_type: "IN" }
	assert.strictEqual(isSessionStale(old), true)
})

test("the ceiling is 16 hours - a shift plus overtime, not a working day", () => {
	// The behavioural tests follow whatever the constant says, so the value
	// itself needs pinning or a typo changes how long a session stays open.
	const ceiling = Number(
		SOURCE.match(/const MAX_OPEN_SHIFT_HOURS = (\d+)/)?.[1]
	)
	assert.strictEqual(ceiling, 16)
})

test("an open session past the component's own ceiling is stale", () => {
	const ceiling = Number(
		SOURCE.match(/const MAX_OPEN_SHIFT_HOURS = (\d+)/)?.[1]
	)
	assert.ok(ceiling, "ceiling constant not found in the component")
	const isSessionStale = buildRule(null)
	assert.strictEqual(
		isSessionStale({ name: "X", time: minutesAgo((ceiling + 1) * 60) }),
		true
	)
	assert.strictEqual(
		isSessionStale({ name: "X", time: minutesAgo((ceiling - 1) * 60) }),
		false
	)
})

test("a missing or unparseable time is stale", () => {
	const isSessionStale = buildRule(null)
	assert.strictEqual(isSessionStale(null), true)
	assert.strictEqual(isSessionStale({ name: "X", time: "not a date" }), true)
})
