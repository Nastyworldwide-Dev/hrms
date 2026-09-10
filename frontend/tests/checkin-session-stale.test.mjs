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
	const body = SOURCE.slice(
		SOURCE.indexOf("function isSessionStale(log) {"),
		SOURCE.indexOf("const nextAction = computed")
	)
	const MAX_OPEN_SHIFT_HOURS = 16
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

test("an open session past the 16-hour ceiling is stale on its own", () => {
	const isSessionStale = buildRule(null)
	assert.strictEqual(
		isSessionStale({ name: "X", time: minutesAgo(17 * 60) }),
		true
	)
	assert.strictEqual(
		isSessionStale({ name: "X", time: minutesAgo(2 * 60) }),
		false
	)
})

test("a missing or unparseable time is stale", () => {
	const isSessionStale = buildRule(null)
	assert.strictEqual(isSessionStale(null), true)
	assert.strictEqual(isSessionStale({ name: "X", time: "not a date" }), true)
})
