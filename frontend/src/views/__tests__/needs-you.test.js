// "Needs you" shows everything waiting, not one kind of it (revamp slice B3).
//
// Since 2.0 this block has rendered exactly ONE row type — remote check-in
// approvals — because `home.needs_you` was never built. An approver with four
// leave applications and an expense claim waiting saw nothing at all, which is
// worse than having no block: a block that looks authoritative and is wrong is
// one people stop checking.
//
// The route names are the thing most likely to rot here. A name that does not
// exist throws at the moment somebody taps it — not at build, not in any other
// test — and these names live in the SERVER's copy map, one repo layer away
// from the router that defines them. So every one is resolved against the
// real router, the same way the quick-links guard does it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const api = readFileSync(join(SRC, "../../hrms/api/needs_you.py"), "utf8")

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const py = (text) => text.replace(/(^|\n)(\s*)#[^\n]*/g, (m, nl, indent) => nl + indent)

const component = code(read("components/NeedsYou.vue"))

//: Every route name the router defines, across its modules — the router is
//: split by area and a literal search of index.js alone would miss six of
//: seven. Read rather than imported: importing the router pulls in Ionic.
function routerNames() {
	const files = [
		"router/index.js",
		"router/attendance.js",
		"router/leaves.js",
		"router/claims.js",
		"router/ot.js",
		"router/issues.js",
		"router/helpdesk.js",
		"router/sop.js",
	]
	const names = new Set()
	for (const file of files) {
		for (const m of read(file).matchAll(/name:\s*"([^"]+)"/g)) names.add(m[1])
	}
	return names
}

test("every route the server sends exists in the router", () => {
	// The failure this prevents is silent until a tap: a row renders, reads
	// correctly, and does nothing — or throws — when somebody acts on it.
	const names = routerNames()
	const routes = [...py(api).matchAll(/\(\s*"[^"]+",\s*"[^"]+",\s*"(\w+)",?\s*\)/g)].map((m) => m[1])
	assert.ok(routes.length >= 7, `expected a route per request type, found ${routes.length}`)
	const missing = routes.filter((name) => !names.has(name))
	assert.deepEqual(missing, [], "a route name that does not exist throws when tapped")
})

test("all seven approvable types are counted", () => {
	// The whole point of the slice. If a type is dropped from the copy map it
	// silently stops being counted, and an approver is told a total that is
	// short.
	const source = py(api)
	for (const doctype of [
		"Leave Application",
		"Expense Claim",
		"Shift Request",
		"OT Request",
		"Attendance Request",
		"Replacement Leave Claim",
		"Compensatory Leave Request",
	]) {
		assert.match(source, new RegExp(`"${doctype}": \\(`), `${doctype} has copy and a route`)
	}
	// And the list of types comes from approval.py rather than a second copy
	// here — two lists of "what is approvable" would drift, and the drift
	// would be a type nobody is told about.
	assert.match(source, /from hrms\.api\.approval import DECIDE_THEN_SUBMIT/)
	assert.match(source, /for doctype, \(field, pending\) in DECIDE_THEN_SUBMIT\.items\(\)/)
})

test("the count asks the same authoriser the decision does", () => {
	// A count derived from its own filter can disagree with the list it opens.
	// An approver told "3 waiting" who finds two rows stops trusting it.
	assert.match(py(api), /_is_routed_approver/, "the real routing test, per document")
})

test("a doctype is never shown to an employee", () => {
	// "Attendance Request" is a table. "attendance fix" is what somebody is
	// waiting for. The noun comes from the server so the wording is in one
	// place, and the component must not invent its own.
	assert.match(component, /row\.noun/, "the component renders the server's word")
	for (const table of ["Leave Application", "Attendance Request", "Replacement Leave Claim"]) {
		const shown = component.match(new RegExp(`__\\("[^"]*${table}`, "g"))
		assert.equal(shown, null, `${table} must not reach a label`)
	}
})

test("the block still renders nothing when nothing is waiting", () => {
	// Absence is the empty state. A permanent "nothing needs you" row is wrong
	// most of the time and costs the fold every day.
	assert.match(component, /v-if="rows\.length"/)
})

test("a realtime event refreshes both counts", () => {
	// A new request changes the unified queue AND the remote check-in badge.
	// Refreshing one leaves the block stating a total short by the thing that
	// just arrived.
	const handler = component.slice(component.indexOf("const onRealtime"))
	assert.match(handler, /pendingCountResource\.reload\(\)/)
	assert.match(handler, /needsYouResource\.reload\(\)/)
})

test("a capped count says so rather than lying", () => {
	// The scan is bounded so Home's first paint does not wait on thousands of
	// per-document permission checks. Past the cap it says "20+", which is the
	// same decision an approver makes anyway.
	assert.match(component, /row\.capped/)
	assert.match(component, /\{0\}\+ \{1\} to approve/)
	assert.match(py(api), /"capped": count > SCAN_CAP/)
})

test("the queue is cached per person", () => {
	// These rows are what is routed to THIS approver. A shared key would show
	// one approver's queue to the next person on the same device.
	assert.match(code(read("data/needsYou.js")), /personalCacheKey\(/)
})
