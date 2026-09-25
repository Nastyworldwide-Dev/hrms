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
	const unresolvedStaleIn = { data: staleData }
	// The ONE session rule (utils/checkinSession.js), injected as the real
	// module's contract: open until 06:00 the next morning (25 Sep 2026: the
	// 16-hour ceiling that stood here offered "Check in" at 01:00-03:00).
	const sessionIsOpen = (log) => {
		const t = log?.time && new Date(String(log.time).replace(" ", "T"))
		if (!t || Number.isNaN(t.getTime())) return false
		const until = new Date(t)
		until.setDate(until.getDate() + 1)
		until.setHours(6, 0, 0, 0)
		return Date.now() < until.getTime()
	}
	return new Function(
		"sessionIsOpen",
		"unresolvedStaleIn",
		`${body}; return isSessionStale`
	)(sessionIsOpen, unresolvedStaleIn)
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

test("the component asks the ONE session rule, not its own ceiling", () => {
	// SUPERSEDED 25 Sep 2026 (employee report: "worked till 3 am, had to check
	// in again"): the 16-hour ceiling disagreed with the server's 06:00 session.
	assert.doesNotMatch(SOURCE, /MAX_OPEN_SHIFT_HOURS/)
	assert.match(SOURCE, /return !sessionIsOpen\(log\)/)
})

test("an IN from yesterday morning is still open before 06:00 and closed after", () => {
	const isSessionStale = buildRule(null)
	const yesterday9 = new Date()
	yesterday9.setDate(yesterday9.getDate() - 1)
	yesterday9.setHours(9, 0, 0, 0)
	const pad = (x) => String(x).padStart(2, "0")
	const s = `${yesterday9.getFullYear()}-${pad(yesterday9.getMonth() + 1)}-${pad(yesterday9.getDate())} 09:00:00`
	const beforeSix = new Date().getHours() < 6
	assert.strictEqual(isSessionStale({ name: "X", time: s }), !beforeSix)
	// two days back is past any session
	assert.strictEqual(isSessionStale({ name: "X", time: minutesAgo(48 * 60) }), true)
})

test("a missing or unparseable time is stale", () => {
	const isSessionStale = buildRule(null)
	assert.strictEqual(isSessionStale(null), true)
	assert.strictEqual(isSessionStale({ name: "X", time: "not a date" }), true)
})
