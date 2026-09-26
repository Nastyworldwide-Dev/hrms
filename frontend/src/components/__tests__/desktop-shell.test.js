// The desktop shell, signed off (2.0 slice D.1, spec §20).
//
// D.1 was blocked on one open question — was 720px the column width, or a
// placeholder? Answered 22 Sep 2026: accepted. So the token stops describing
// itself as provisional, and the rest of this slice is VERIFICATION rather
// than construction: the shell was built in phase 4 and the tab change (slice
// 0.1) flowed into it automatically, because SideNav reads the same
// TAB_ITEMS and MORE_ITEMS the phone bar does.
//
// That last part is the thing worth pinning. The side nav and the tab bar
// agreeing is not a coincidence to be maintained by hand — it is a
// consequence of both reading one list, and a future edit that gives the
// desktop its own copy would let the two drift for months before anybody
// on a laptop noticed.
//
// §20.2's own text still names the PRE-2.0 destinations (HOME · ATTEND ·
// LEAVE · PAY, then KPI, Issues, SOPs, Expenses...). That is the spec
// describing a bar that no longer exists; the code follows the ruling, and
// the spec is corrected alongside this.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const tokens = JSON.parse(readFileSync(join(SRC, "../../design/tokens.json"), "utf8"))

test("the desktop column is a decision, not a placeholder", () => {
	const column = tokens.layout["content-column-lg"]
	// 672 from 26 Sep 2026 (owner ruling R2): Apple's readable width; was 720
	assert.equal(column.value, "672px", "the width the owner ruled")
	assert.doesNotMatch(
		column.description,
		/starting value|expected to be tuned|provisional/i,
		"it was accepted on 22 Sep 2026; a token that still calls itself provisional invites a re-litigation"
	)
	assert.match(column.description, /signed off|accepted|ruling/i, "and says so")
})

test("the desktop and the phone read one list", () => {
	// Two copies of the navigation would drift, and the drift would live on
	// desktop — the surface fewest people look at — until somebody opened a
	// laptop months later.
	const nav = read("components/SideNav.vue")
	assert.match(nav, /from "@\/data\/navItems"/, "the side nav imports the shared list")
	assert.match(nav, /TAB_ITEMS/, "the same primaries the bar shows")
	assert.match(nav, /MORE_ITEMS/, "and the same rest")
	assert.doesNotMatch(
		nav,
		/title: "(Home|Calendar|Requests|Score)"/,
		"it does not keep its own copy"
	)
})

test("the side nav shows the 2.0 destinations, because it shares the list", () => {
	// A consequence, asserted: slice 0.1 changed one file and the desktop
	// followed. If this ever fails, somebody gave the desktop its own list.
	const items = read("data/navItems.js")
	for (const title of ["Calendar", "Requests", "Score"]) {
		assert.match(items, new RegExp(`title: "${title}"`), `${title} is in the shared list`)
	}
})

test("the tab bar is hidden where the side nav takes over", () => {
	// §20.2: one navigation surface at a time. Both visible would also break
	// the §15 count, where the side nav REPLACES the bar rather than adding to
	// it — net zero against the budget.
	assert.match(read("components/BottomTabs.vue"), /lg:hidden/, "the bar goes at lg:")
	assert.match(read("components/SideNav.vue"), /hidden lg:|lg:flex/, "and the rail arrives")
})

test("the side nav is a glass surface, and the only one it adds", () => {
	// §20.2's surface accounting: the rail replaces the bar. If the rail were
	// opaque it would be a second navigation treatment; if it were TWO glass
	// surfaces it would spend a screen's budget on chrome.
	const css = read("theme/glass-components.css").replace(/\/\*[\s\S]*?\*\//g, (b) =>
		b.replace(/[^\n]/g, " ")
	)
	const rail = css.slice(
		css.indexOf("\n.g-sidenav {"),
		css.indexOf("}", css.indexOf("\n.g-sidenav {"))
	)
	assert.match(rail, /backdrop-filter|--g-blur/, "glass, per the §6 recipe")
	const nav = read("components/SideNav.vue")
	assert.equal(
		(nav.match(/class="[^"]*\bg-glass\b/g) || []).length,
		0,
		"the surface is the rail's own class; the component does not paint a second one"
	)
})
