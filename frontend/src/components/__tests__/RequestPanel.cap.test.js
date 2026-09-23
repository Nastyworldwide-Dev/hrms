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

//: The "Show N more" control specifically. `g-list-more` is its own class and
//: the one that carries the floor; matching "the first button in the file"
//: broke the moment the filter chips were added above it.
function showMoreButton() {
	const match = panel().match(/<button[\s\S]*?class="([^"]*g-list-more[^"]*)"/)
	assert.ok(match, "the control is a button carrying g-list-more")
	return match
}
const list = () => read("../RequestList.vue")

test("the panel caps what it renders, and the cap is five", () => {
	assert.match(
		panel(),
		/const HOME_ROWS = 5\b/,
		"the cap is a named constant, not a literal in a slice"
	)
	assert.match(
		panel(),
		/\.slice\(0,\s*HOME_ROWS \+ PAGE \* pages\.value\)/,
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
	assert.match(text, /__\(\s*["']Show more \(\{0\} left\)["']/, "the label carries the count")
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

// §14: touch targets are 44x44 including chevrons and dismiss controls. The
// control computes to EXACTLY 44 — py-3 (12 either side) plus text-sm at
// 14px/1.43 — which is the minimum met by arithmetic rather than by
// intention, and one padding step away from failing. Pin the two values that
// produce it, so a later tidy cannot shave it to 40 without a red test.
//
// Height is also why the floor is a minimum rather than a fixed height: a
// fixed one would pass the test while leaving the LABEL vertically adrift in
// a taller box.
test("the control meets the 44px touch target", () => {
	// NOT /<button[\s\S]*?>/: the lazy match ends at the ">" inside
	// `v-if="hidden > 0"` and never reaches the class attribute.
	//
	// And not the FIRST button either — the filter chips (mockup 4 gap #3) are
	// buttons too and they come first in the template, so a first-match test
	// silently started measuring a chip instead of the control it names. It is
	// anchored on the control's own class now.
	const classes = showMoreButton()
	assert.ok(classes, "the control is a button element with a class attribute")
	assert.match(classes[1], /\bpy-3\b/, "12px either side of the label")
	assert.match(classes[1], /\btext-sm\b/, "14px at 1.43 = 20px; 20 + 24 = 44 exactly")
	assert.match(classes[1], /\bg-focusable\b/, "§14.3's two-tone ring, not a removed outline")
})

// It is full-width, so the 44px height is the whole target: there is no narrow
// hit area next to a wide row. `w-full` carries that.
test("the target is the full row, not a word in the middle of one", () => {
	assert.match(showMoreButton()[1], /\bw-full\b/)
})

// The control renders `v-if="hidden > 0"`, so activating it destroys the
// element that had focus. Focus then falls back to <body> and a keyboard or
// screen-reader user is returned to the top of the page having pressed a
// button that, as far as they can tell, did nothing. §14.1: focus visible,
// never removed without a replacement. Design review of 70bffe660.
test("expanding puts focus somewhere, not nowhere", () => {
	const text = panel()
	assert.match(text, /@click="expand"/, "activation runs a handler, not an inline assignment")
	const fn = text.slice(text.indexOf("async function expand()"))
	assert.match(fn, /await nextTick\(\)/, "the rows must exist before anything is focused")
	assert.match(fn, /\.focus\(\)/, "and focus moves to them")
	assert.match(text, /tabindex="-1"/, "the list is focusable by script, not by tab order")
})

// Rows appearing in the DOM announce nothing by themselves, and the control
// that would have announced them is the thing that just disappeared. The
// panel already owes this courtesy elsewhere — the "Refreshing…" line two
// rows above carries role="status".
test("expanding says what happened", () => {
	const text = panel()
	// The panel carries TWO role="status" — the "Refreshing…" line already had
	// one — so matching the bare attribute passed even with this region
	// deleted. Pin the region that carries THIS message.
	assert.match(
		text,
		/<p class="sr-only" role="status">\{\{ revealed \}\}<\/p>/,
		"a polite live region reports the change"
	)
	assert.match(text, /__\(\s*["']\{0\} more requests shown["']/, "with the count, not just a ping")
	assert.match(text, /aria-controls="request-panel-list"/, "the control names what it expands")
	assert.match(text, /aria-expanded=/, "and its state")
})

// The reset must clear the announcement too, or switching tabs leaves a live
// region asserting a reveal that no longer happened.
test("switching tab clears the announcement with the expansion", () => {
	const watcher = panel().slice(panel().indexOf("watch(activeTab"))
	assert.match(watcher.slice(0, 160), /showAll\.value = false/)
	assert.match(watcher.slice(0, 160), /revealed\.value = ""/)
})

// The 44px floor is explicit, not arithmetic. py-3 + text-sm computes to
// exactly 44 — the minimum met by luck, one utility away from failing, and at
// §14.1's 120% dynamic type the label grows while the padding does not.
test("the 44px floor is guaranteed, not computed", () => {
	const classes = showMoreButton()[1]
	// A named class, not a utility: the lint gate counts every bracketed
	// arbitrary-value utility, including one that references a token, and it is
	// right to — the floor has one definition (--g-touch-target-min) and a
	// utility spelling it at the call site is a second place for it to drift.
	assert.match(classes, /\bg-list-more\b/, "the class that carries the floor")
	const css = readFileSync(
		fileURLToPath(new URL("../../theme/glass-components.css", import.meta.url)),
		"utf8"
	)
	assert.match(
		css,
		/\.g-list-more\s*\{[^}]*min-height:\s*var\(--g-touch-target-min\)/,
		"and it resolves to the token, not to a literal 44px"
	)
})

// ---------------------------------------------------------------------------
// The filter chips (mockup 4 gap #3, 23 September 2026). Mockup 4's own audit
// found its chips at 33px with no minimum declared — the exact defect this
// file exists to prevent on the control above.

test("a filter chip is a 44px target too", () => {
	const css = readFileSync(
		fileURLToPath(new URL("../../theme/glass-components.css", import.meta.url)),
		"utf8"
	)
	const chip = css.slice(css.indexOf("\n.g-chip {"), css.indexOf("\n.g-chip--on"))
	assert.match(
		chip,
		/min-height:\s*var\(--g-touch-target-min\)/,
		"through the token that defines the floor, not a literal"
	)
})

test("the chips wrap, never scroll sideways", () => {
	// A horizontal scroller inside a vertical page is a named anti-pattern —
	// lost place, broken scroll restore, screen-reader trouble — and mockup 4's
	// 21 September rework removed the last two from that file. Adding one back
	// here would undo it.
	const css = readFileSync(
		fileURLToPath(new URL("../../theme/glass-components.css", import.meta.url)),
		"utf8"
	)
	const chips = css.slice(css.indexOf("\n.g-chips {"), css.indexOf("\n.g-chip {"))
	assert.match(chips, /flex-wrap:\s*wrap/)
	assert.doesNotMatch(chips, /overflow-x/, "no sideways scroller")
})

test("a chip is a toggle, not a tab", () => {
	// They narrow ONE list; they do not move between panels. role="tab" would
	// promise a tabpanel that is not there — the distinction mockup 4's notes
	// draw, and the reason its nav uses aria-current instead.
	const text = panel()
	const chips = text.slice(
		text.indexOf('class="g-chips"'),
		text.indexOf("</div>", text.indexOf('class="g-chips"'))
	)
	assert.match(chips, /role="group"/)
	assert.match(chips, /:aria-pressed="filter === chip\.key"/)
	assert.doesNotMatch(chips, /role="tab"/)
})

test("the filter resets when the tab changes", () => {
	// Carrying "Not approved" into the Team tab opens it on an empty list that
	// looks broken — the same reason `showAll` already resets there.
	const text = panel()
	const watcher = text.slice(
		text.indexOf("watch(activeTab"),
		text.indexOf("function updateRequestDetails")
	)
	assert.match(watcher, /filter\.value = "all"/)
})

test("counting a chip does not mutate the filter", () => {
	// The first version swapped `filter.value` to count each chip and put it
	// back — a side effect inside a computed, which would have made the
	// rendered list flicker through three filters on every recount. eslint
	// caught it; this keeps it caught.
	const text = panel()
	const counts = text.slice(
		text.indexOf("const filterCounts"),
		text.indexOf("const activeRequests")
	)
	assert.doesNotMatch(counts, /filter\.value =/, "counting is pure")
	assert.match(counts, /matches\(request, key\)/, "the key is passed, not read from the ref")
})

// No endless list (owner, 23 Sep; NN/g infinite scrolling; Baymard
// load-more): "Show more" adds twenty at a time, not every request at once.
test("Show more reveals twenty at a time, never the whole history", () => {
	const text = panel()
	assert.match(text, /const PAGE = 20\b/)
	assert.match(text, /\.slice\(0,\s*HOME_ROWS \+ PAGE \* pages\.value\)/)
})
