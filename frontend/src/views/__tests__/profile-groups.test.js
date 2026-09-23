// Profile is four groups, not one list (revamp §7, slice D3).
//
// It was a single undifferentiated column of nine rows, each a hand-built div
// with its own padding, border and hover — 17 of the app's 103 stray pixel
// values lived on this one screen. Somebody looking for "change my password"
// had to read all nine, and one of them (Change Password) was not even there:
// it was a row inside Settings.
//
// The four groups answer four different questions — who am I, where do I
// work, how does the app behave, how do I get out — which is what makes them
// groups rather than a divided list.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const view = code(read("views/Profile.vue"))

test("there are four groups, each with a name", () => {
	const keys = [...view.matchAll(/key: "(you|work|app|account)"/g)].map((m) => m[1])
	assert.deepEqual(keys, ["you", "work", "app", "account"], "in that order")
})

test("the rows come from the system's list components", () => {
	// The hand-built rows carried their own padding, dividers and hover, which
	// is why they drifted from every other list in the app — and why this one
	// screen held 17 stray pixel values.
	assert.match(view, /<GListPanel>/)
	assert.match(view, /<GListRow/)
	assert.doesNotMatch(view, /class="flex flex-row cursor-pointer p-4/, "no hand-built rows")
})

test("an empty group is not drawn", () => {
	// The Work group is empty for an employee who is nobody's approver and has
	// no HR contacts screen. A heading over nothing is a heading that makes
	// the reader look for something that is not there.
	assert.match(view, /v-if="group\.rows\.length"/)
})

test("the version is on the screen people report defects from", () => {
	// Every phone-side defect this month began with "which version are you
	// on". The answer is now where somebody already is when they hit one.
	assert.match(view, /About this app/)
	assert.match(view, /__APP_BUILD__/, "the compile-time stamp")
	// The SAME constant the diagnostics report carries, so the version read
	// off the screen matches the version in the report that follows it.
	assert.match(code(read("utils/diagnostics.js")), /__APP_BUILD__/)
})

test("change password has its own row", () => {
	// It was a row inside Settings, which is two taps and a guess. It is the
	// single most-looked-for thing on an account screen.
	assert.match(view, /key: "password"/)
	assert.match(view, /name: "ChangePassword"/)
})

test("nothing was removed in the regroup", () => {
	// Every destination the flat list reached is still reachable. A tidy-up
	// that loses a screen is not a tidy-up.
	for (const destination of ["HRContacts", "Approvals", "Settings", "ChangePassword"]) {
		assert.match(view, new RegExp(`name: "${destination}"`), `${destination} survives`)
	}
	assert.match(view, /profileLinks\.map/, "and the three detail sheets do too")
})

test("the role gate is still the server's verdict", () => {
	// `isApprover` is a RESOURCE — answered by the backend — not a role string
	// read here. The regroup moved the row; it did not move the decision.
	assert.match(view, /isApprover\.data/)
	assert.doesNotMatch(view, /"HR Manager"|"HR User"/, "no role literal")
})
