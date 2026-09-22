// QuickLinks is Home's biggest single line item in the fold budget (plan §2, C1).
//
// Home passes SEVEN links: Home.vue's baseQuickLinks is six, plus one
// unconditional HR row. As full-width GListRows that is 7 x 50px (min-height 44
// against --g-pad-row's 11.5px and a 27px icon well) = ~350px, on a phone whose
// entire usable height, once the header and tab bar are paid for, is ~440px
// (invariant F1). One panel was taking four fifths of the screen.
//
// A 4-across grid carries the same seven destinations in two rows: ~120px with
// one-line labels, ~145px when they wrap. That is the "action and information
// over text" the owner asked for — the information is WHERE each tile goes, and
// a row 320px wide showing one 18px icon and two words is mostly empty.
//
// The counts above are computed from the tokens, not estimated: an earlier
// draft of this file said eight links and 450px and both were wrong. The same
// mistake in an icon inventory took three passes to catch (43fd4093c).
//
// These tests pin the structure that produces the height, and the two things a
// density change is most likely to break: the surface budget (§15 — a grid of
// eight glass CARDS would be 8 surfaces, not 1) and the touch target.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const quicklinks = () => src("../QuickLinks.vue")
// The panel itself is a primitive: the usage gate's rule is that
// components/glass/** owns .g-glass and everyone else composes it. The first
// version of this grid built the surface inline in QuickLinks and the gate
// caught it, which is the gate doing its job.
const tilegrid = () => src("../glass/GTileGrid.vue")
const homeView = () => src("../../views/Home.vue")
const css = () => src("../../theme/glass-components.css")
const tokens = () => src("../../theme/glass.css")

// Strip comments before asserting on markup: an earlier test in this repo
// matched its own explanatory prose, because a comment documenting a removal
// names the thing it removed. A test its subject's comments can fail is not a
// test.
const markup = (s) => s.replace(/<!--[\s\S]*?-->/g, "")

test("QuickLinks does not spend the fold on one full-width row per link", () => {
	assert.doesNotMatch(
		markup(quicklinks()),
		/<GListRow\b/,
		"seven 50px rows is ~350px on a ~440px budget; use a tile grid"
	)
})

test("the tile grid is ONE glass surface, not one per link", () => {
	// §15.1: a .g-glass under v-for is N surfaces at runtime. The cells go
	// inside a single .g-cellgrid, exactly as GBalanceGrid does it (§15.2).
	assert.match(markup(tilegrid()), /g-cellgrid/, "reuse the existing one-surface cell grid")
	// And QuickLinks must compose that panel rather than rebuild one: a second
	// .g-glass here would be a second surface on Home whatever it contained.
	assert.match(markup(quicklinks()), /<GTileGrid\b/, "compose the primitive that owns the surface")
	assert.doesNotMatch(
		markup(quicklinks()),
		/(?<!-)\bg-glass\b(?!-)/,
		"components/glass/** owns .g-glass; screens compose it (design/gates/usage.mjs)"
	)
	for (const tag of markup(tilegrid()).match(/<[^>]*v-for[^>]*>/g) || []) {
		assert.doesNotMatch(
			tag,
			/g-glass/,
			"a glass surface under v-for is N surfaces at runtime (§15.1)"
		)
	}
})

test("every tile is a real button, so the whole tile is the target", () => {
	// A tile whose <div> carries @click is not keyboard-reachable and has no
	// role. GListRow gave us a <button> for free; the grid must not lose it.
	assert.match(
		markup(quicklinks()),
		/<button[\s>]/,
		"tiles must be <button>, not clickable divs (WCAG 2.1.1)"
	)
})

test("the tile meets the 44px touch target from the token, not a guess", () => {
	const block = css().match(/\.g-cell--quick\s*\{[^}]*\}/)
	assert.ok(block, ".g-cell--quick should exist in the theme, not inline in the SFC")
	assert.match(
		block[0],
		/min-height:\s*var\(--g-touch-target-min\)/,
		"layout.touch-target-min is 44px and is already stricter than WCAG 2.5.8 AA (24px); read the token"
	)
})

test("four across, so seven links are two rows", () => {
	const block = css().match(/\.g-cellgrid--quick\s*\{[^}]*\}/)
	assert.ok(block, ".g-cellgrid--quick should define the column count")
	assert.match(block[0], /repeat\(4,\s*1fr\)/, "4 columns x 2 rows carries all seven")
	// ...and the component has to ASK for that grid. Without this line the
	// suite survived swapping --quick for --balance: two columns, eight tiles,
	// four rows, the whole saving gone, five green tests. A rule nothing is
	// pinned to is documentation.
	assert.match(
		markup(tilegrid()),
		/g-cellgrid--quick/,
		"the 4-column rule only applies if the panel asks for the modifier"
	)
})

// The skeleton tile count is a claim about Home's link count, and claims about
// counts are exactly what went wrong here twice: the first draft of this file
// said eight. Read the number out of Home.vue instead of trusting the comment,
// so adding a quick link fails this test rather than silently making the panel
// jump a row on load.
test("the skeleton shows as many tiles as Home actually passes", () => {
	const home = homeView().replace(/<!--[\s\S]*?-->/g, "")
	const base = (home.match(/const baseQuickLinks\s*=\s*\[([\s\S]*?)\n\]/) || [])[1]
	assert.ok(base, "baseQuickLinks should still be a literal array in Home.vue")
	const extra = (home.match(/const quickLinks\s*=\s*computed\(\(\)\s*=>\s*\[([\s\S]*?)\n\]\)/) ||
		[])[1]
	assert.ok(extra, "quickLinks should still spread baseQuickLinks and add its own")
	const count = (base.match(/\broute:/g) || []).length + (extra.match(/\broute:/g) || []).length
	const dflt = Number(
		(tilegrid().match(/tiles:\s*\{\s*type:\s*Number,\s*default:\s*(\d+)/) || [])[1]
	)
	assert.equal(dflt, count, `Home passes ${count} links; GTileGrid's skeleton default is ${dflt}`)
})

// A design review asked whether a long label could clip. The line-clamp caps
// LINES; it does nothing for a single word wider than the 74px column, which
// would overflow sideways instead of wrapping into the second line. No label
// Home passes today hits it, so only a rule can keep the guard honest.
test("a label too long to break at a space still wraps instead of overflowing", () => {
	const block = css().match(/\.g-cell__label\s*\{[^}]*\}/)
	assert.ok(block, ".g-cell__label should exist in the theme")
	assert.match(
		block[0],
		/overflow-wrap:\s*break-word/,
		"-webkit-line-clamp limits lines, not the width of one unbreakable word"
	)
})

// The focus-ring comment next to .g-cell--quick makes a claim ABOUT THE TOKENS:
// --g-ink flips per theme, --g-brand does not. A design reviewer caught an
// earlier draft asserting that both flip, which was false. Prose cannot be
// trusted to stay true, so the claim is pinned here: if someone later gives
// --g-brand a dark value, this fails and the comment gets revisited rather than
// quietly becoming wrong a second time.
test("the focus ring's two halves behave the way the comment says they do", () => {
	const t = tokens()
	assert.equal(
		(t.match(/^\s*--g-ink:/gm) || []).length,
		2,
		"--g-ink should be defined at :root and redefined once in the dark block"
	)
	assert.equal(
		(t.match(/^\s*--g-brand:/gm) || []).length,
		1,
		"--g-brand is the accent and is deliberately constant across themes; if that changed, the .g-cell--quick focus-ring comment now describes something else"
	)
})
