// The balance strip (revamp slice C1, §5).
//
// The heuristic this exists for is recognition over recall (Nielsen #6): the
// leave balance lived on the leave dashboard while the decision to take leave
// was made on the form, so a person had to memorise a figure and carry it
// between two screens. The ones who did not bother filed requests that got
// rejected.
//
// What is pinned here is the part a later edit breaks silently: that a
// missing section reads as ABSENT rather than zero, that every counter is a
// door, and that the strip disappears when it has nothing to say.
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

const component = code(read("components/RequestBalances.vue"))
const api = readFileSync(join(SRC, "../../hrms/api/requests_summary.py"), "utf8").replace(
	/(^|\n)(\s*)#[^\n]*/g,
	(m, nl, indent) => nl + indent
)

test("a counter nobody can act on is not built", () => {
	// Every row is a door into the list it counts. A number with no destination
	// makes the reader do the work of finding what it refers to.
	const rows = component.slice(component.indexOf("const rows = computed"))
	const pushes = (rows.match(/out\.push\(\{/g) || []).length
	const gos = (rows.match(/go: \(\) =>/g) || []).length
	assert.ok(pushes >= 3, "three counters")
	assert.equal(gos, pushes, "every counter goes somewhere")
})

test("a zero is not a row", () => {
	// A strip of permanent zeros is a strip nobody reads, and it costs the
	// space the useful numbers need.
	const rows = component.slice(component.indexOf("const rows = computed"))
	assert.match(rows, /unclaimed_days > 0/)
	assert.match(rows, /approved_unpaid_amount > 0/)
	assert.match(rows, /attendance\?\.days > 0/)
})

test("Leave left always answers; the attention rows only when non-zero", () => {
	// SUPERSEDED 25 Sep 2026 (alpha.8 r3, measured): the strip vanishing when
	// empty made Requests jump 71 pt as the skeleton gave way to nothing, and
	// left "where do I check my leave?" with no answer. Leave left is always
	// drawn — "None allocated yet" when HR has not allocated any; the
	// attention rows (and their header) still only when there is one.
	assert.doesNotMatch(component, /hasAnything/)
	assert.match(component, /__\("None allocated yet"\)/)
	assert.match(component, /<template v-if="rows\.length">/)
})

test("a failed read is not the same as having nothing", () => {
	// Both rendered nothing, so an employee with 12 days of leave and a broken
	// endpoint saw the same screen as one with none — on the strip that exists
	// precisely so nobody has to guess at those numbers.
	assert.match(component, /v-if="requestsSummary\.error"/, "the error is its own branch")
	assert.ok(
		component.indexOf("requestsSummary.error") < component.indexOf('v-else-if="firstLoad"'),
		"and it is checked first"
	)
	assert.match(component, /could not be loaded/, "it says so")
	assert.match(component, /try again/i, "and what to do")
})

test("a section the server could not read is absent, never zero", () => {
	// "You have no overtime to claim" when the truth is "we could not check"
	// sends somebody away from money they are owed. The server omits the key,
	// and the component's optional chaining means an omitted key builds no row.
	assert.match(api, /logger\.exception\("\[requests_summary\] %s failed; omitted", key\)/)
	assert.doesNotMatch(api, /summary\[key\] = \{\}/, "an empty section would read as zero")
	assert.match(component, /data\.value\.overtime/, "read optionally")
	assert.match(component, /overtime\?\./, "so an absent section builds no row")
})

test("nothing here recomputes a number that already exists", () => {
	// A second implementation of "how much leave is left" is a second answer.
	// Every figure is composed from the endpoint that already owns it.
	assert.match(api, /from hrms\.api import get_current_employee, get_leave_balance_map/)
	assert.match(api, /from hrms\.api import get_claimable_ot_summary/)
	assert.match(api, /from hrms\.api import get_expense_claims/)
})

test("the leave denominator is the annual entitlement", () => {
	// A mid-year joiner with 7 of 14 has used none of it. "7 of 7" says the
	// opposite, and it is what reading `allocated_leaves` as the total gives.
	assert.match(api, /flt\(entry\.get\("annual_entitlement"\)\) or allocated/)
	// Owner ruling 23 Sep 2026 (one-screen Requests): the cards are gone; the
	// denominator is printed in the All balances sheet as "{0} of {1} left".
	assert.match(component, /__\("\{0\} of \{1\} left", \[trim\(row\.balance\), trim\(row\.total\)\]\)/)
})

test("expiry comes from the allocation, not from a key that is not there", () => {
	// The balance map carries from_date and NOT to_date — verified on the
	// bench after the first version read a key that never exists and reported
	// nothing as expiring, ever.
	assert.doesNotMatch(api, /entry\.get\("to_date"\)/, "that key is not in the map")
	assert.match(api, /"Leave Allocation"/, "the end date lives on the allocation")
	assert.match(api, /expiry\.setdefault\(row\.leave_type, row\.to_date\)/, "earliest wins")
})

test("only a near expiry is news", () => {
	// A balance expiring in nine months is a fact; one expiring in three weeks
	// is a prompt, and showing both as prompts makes neither one.
	assert.match(api, /EXPIRY_HORIZON_DAYS = 45/)
	assert.match(api, /0 <= days_left <= EXPIRY_HORIZON_DAYS and balance > 0/)
	// Owner ruling 23 Sep 2026: the expiry shows in the All balances sheet row.
	assert.match(component, /if \(row\.expiring_soon\)/)
})

test("an unmarked day means a day somebody actually worked", () => {
	// A day nobody worked is a day off, not a gap. Counting it would put a
	// number on the screen that never reaches zero and that nobody can act on.
	assert.match(api, /"Employee Checkin"/)
	assert.match(api, /worked_days if day not in marked/)
})

test("the strip comes straight after New request", () => {
	// REVERSED by the owner-approved one-screen layout (23 Sep 2026): the
	// button is first, the one balances line right under it.
	const view = code(read("views/Requests.vue"))
	assert.ok(
		view.indexOf("__('New request')") < view.indexOf("<RequestBalances"),
		"New request first, then balances"
	)
})

// ---------------------------------------------------------------------------
// Deployed 23 September 2026: seven leave cards, two of them wrapping to three
// lines, above anything actionable — a wall where the plan asked for a strip.
// And every number was bare: "60 HOSPITALIZATION" reads as alarming until you
// know it is 60 of 60, i.e. untouched.

test("a balance states what it is out of", () => {
	// The plan's words are "12.5 of 16 left". A number with no scale is not a
	// balance, it is a number.
	// Owner ruling 23 Sep 2026: the page line is the remaining number only
	// ("Annual 6"); the scale lives in the All balances sheet.
	assert.match(component, /__\("\{0\} of \{1\} left"/)
})

test("a whole number does not render a trailing .0", () => {
	// "of 16" reads as a count; "of 16.0" reads as a measurement. Half-days
	// are real, so the decimal stays when it means something. The trim now
	// lives in utils/requestsPage.js (tested by running it there).
	assert.match(component, /trimNumber as trim/)
	const fn = read("utils/requestsPage.js")
	assert.match(fn, /Number\.isInteger\(n\) \? String\(n\) : n\.toFixed\(1\)/)
})

test("an expiry replaces the denominator rather than joining it", () => {
	// A date is the more urgent of the two, so it wins the line (sheet row,
	// since the cards went — owner ruling 23 Sep 2026).
	const fn = component.slice(component.indexOf("function balanceLine"))
	assert.match(fn, /if \(row\.expiring_soon\)[\s\S]*?return[\s\S]*?return __\("\{0\} of \{1\} left"/)
})

test("owner ruling R2: Annual and Medical, then All balances; the full list is compact too", () => {
	// 23 Sep: "B, even on expand can be better compact so we stay consistent".
	// Two cards fit one row on a phone; the rest open in a sheet as the same
	// compact rows, never a wall of big cards.
	assert.match(component, /const LEAVE_SHOWN = 2/)
	assert.match(component, /__\(["']All balances["']\)/)
	assert.match(component, /<GModal :is-open="allOpen"[\s\S]*<GListRow[\s\S]*v-for="row in rankedLeave"/)
	assert.doesNotMatch(component, /__\("Show fewer leave types"\)/)
})

test("Annual and Medical lead, whatever the site calls them", () => {
	const ranked = component.slice(component.indexOf("const rankedLeave"))
	assert.match(component, /const PINNED = \[\/annual\|privilege\|earned\/i, \/medical\|sick\/i\]/)
	assert.match(ranked, /pin\(a\) - pin\(b\)/)
})

test("the types you have actually used come first", () => {
	// An untouched statutory entitlement is a fact you can look up; a type you
	// have drawn on is the one you are checking. Expiring types outrank both,
	// because only they have a deadline.
	const ranked = component.slice(component.indexOf("const rankedLeave"))
	assert.match(ranked, /a\.expiring_soon !== b\.expiring_soon/, "expiry first")
	assert.match(ranked, /usedA > 0/, "then types with usage")
})
