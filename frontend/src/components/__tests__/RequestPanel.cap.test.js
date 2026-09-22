// Home's request list is capped, and nothing it hides becomes unreachable
// (plan slice S6, C3).
//
// WHAT THE RULE ACTUALLY IS. The owner's goal, recorded in
// home-fold-budget.test.js, is "no scroll at best, but we dont want to against
// screen reso height and width screen size" — the fold is a BUDGET, not a
// length. The ANCHOR (banner, check-in, quick links) fits the smallest usable
// height without scrolling; the request panel sits below it and is scrolled
// to, by design. So this slice is not trying to remove the scroll. It is
// removing an UNBOUNDED one: the panel rendered every request a person had,
// and ten of them is ~620px of page — another whole screen past the thing they
// opened Home for.
//
// WHY FIVE. Measured, not chosen: a row is two lines of text plus py-3 either
// side, ~62px. Five rows is ~310px, which sits inside the ~440px small-phone
// budget alongside the panel's own eyebrow and tab strip. Three would fit too
// and was the plan's figure, but it hides rows from people who would never
// have scrolled anyway; most people have nought to two requests and never see
// the control at all.
//
// WHY EXPAND, NOT "SEE ALL". Each tab MERGES six doctypes — leaves, claims,
// shift requests, attendance requests, OT and replacement leave claims. There
// is no combined list route, and pointing "See all (9)" at one type's screen
// would answer a tap about nine requests with a page showing three. A control
// that misstates where it goes is worse than a longer page. Expanding in place
// is also this app's own idiom (TeamDashboard's rows, SideNav's rail).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const panel = () => read("../RequestPanel.vue")
const list = () => read("../RequestList.vue")

test("the panel caps what it renders, and the cap is five", () => {
	assert.match(
		panel(),
		/const HOME_ROWS = 5\b/,
		"the cap is a named constant, not a literal in a slice"
	)
	assert.match(
		panel(),
		/\.slice\(0,\s*HOME_ROWS\)/,
		"the list passed to RequestList is the capped one, not the whole set"
	)
})

test("nothing the cap hides is unreachable", () => {
	const text = panel()
	assert.match(text, /showAll/, "there is a control that reveals the rest")
	assert.match(
		text,
		/showAll\.value\s*=\s*true|showAll\s*=\s*true/,
		"and pressing it expands in place — no route, because there is no combined list to route to"
	)
})

test("the control says how many, and how many is the truth", () => {
	const text = panel()
	// "Show 4 more", not "Show more": a count the person can check against
	// what appears is the difference between a control and a promise.
	assert.match(text, /hidden(Count)?/, "the number of hidden rows is computed")
	assert.match(text, /__\(\s*["']Show \{0\} more["']/, "the label carries the count")
})

test("the count is what is hidden, not what exists", () => {
	// `length - HOME_ROWS`, never `length`: a person with 7 requests seeing
	// "Show 7 more" taps it and finds 2 new rows.
	assert.match(panel(), /\.length\s*-\s*HOME_ROWS/, "hidden = total - shown")
})

test("the cap is Home's, not the list component's", () => {
	// RequestList is used by the full-screen lists too. A cap inside it would
	// silently truncate those, where the whole point is to show everything.
	assert.doesNotMatch(list(), /HOME_ROWS|\.slice\(0,\s*\d+\)/, "the full lists must stay full")
})

test("expanding does not re-collapse when the tab changes under it", () => {
	// The tab strip swaps the list; a stale `showAll` would open the next tab
	// already expanded, which is the opposite of what the cap is for.
	assert.match(
		panel(),
		/watch\(\s*activeTab[\s\S]{0,200}showAll/,
		"switching tab returns to the capped view"
	)
})
