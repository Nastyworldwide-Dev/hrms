// Two different empties, and saying the wrong one is a false statement about
// somebody's job (revamp §7, slice D2).
//
// The owner's instruction was "respect the backend bro — they can view what
// they are allowed to". The defect was the opposite of a leak: an employee
// who is nobody's manager opened Team and was told "Nothing waiting on you —
// approvals will appear here when your team submits", which is a sentence
// about a team they do not have.
//
// The screen could not tell the two cases apart because the SERVER returned
// the same payload for both. Fixed there; what is pinned here is that the
// screen never decides it for itself.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const api = readFileSync(join(SRC, "../../hrms/api/team.py"), "utf8").replace(
	/(^|\n)(\s*)#[^\n]*/g,
	(m, nl, indent) => nl + indent
)

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const view = code(read("views/team/TeamDashboard.vue"))

test("the screen never decides who has a team", () => {
	// Revamp P5: permission is the server's answer. A role check here would be
	// a second opinion that can disagree with the fence, and the one that
	// disagrees is always the one somebody notices last.
	assert.doesNotMatch(view, /HR Manager|HR User|hasHRRole|reports_to/, "no role logic")
	assert.match(view, /teamStatus\.data\?\.entitled === false/, "it reads the server's flag")
})

test("an absent flag is not treated as a refusal", () => {
	// `=== false` deliberately. While the payload is loading the flag is
	// undefined, and `!entitled` would flash "you do not have a team" at every
	// manager on every single load.
	assert.match(view, /=== false/)
	assert.doesNotMatch(view, /!teamStatus\.data\?\.entitled/, "that flashes on every load")
})

test("the two empties say two different things", () => {
	assert.match(view, /You do not have a team here/, "not a manager")
	assert.match(view, /Nobody on your team today/, "a manager on a quiet day")
	// And the old sentence — the false one — is gone.
	assert.doesNotMatch(
		view,
		/Approvals will appear here when your team submits/,
		"that told a non-manager they had a team"
	)
})

test("the refusal says what to do about it", () => {
	// An employee who believes this is wrong needs somewhere to go. "You do
	// not have a team" with no next step is a dead end.
	const block = view.slice(view.indexOf("You do not have a team here"))
	assert.match(block, /Ask HR/, "there is a way out")
})

test("entitlement has one definition, not two", () => {
	// `is_approver` already answers "does anything route to this person" for
	// the RequestPanel's team tabs. Two definitions would drift, and the drift
	// would be somebody told they have no team while their approvals pile up.
	assert.match(api, /entitled = is_approver\(\)/)
})

test("every return from the status endpoint carries the flag", () => {
	// A path that omits it leaves the screen reading `undefined`, which is
	// neither empty state — so the screen renders nothing at all.
	const fn = api.slice(api.indexOf("def get_team_status"), api.indexOf("def get_team_roster"))
	const returns = fn.match(/return \{|return \{\*\*empty/g) || []
	const flags = fn.match(/"entitled"/g) || []
	assert.ok(returns.length >= 2, "there are several ways out of this function")
	assert.ok(flags.length >= 2, "and each says whether the caller is entitled")
})
