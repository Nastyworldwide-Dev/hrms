// A rename must reach the NAV, the PAGE TITLE and the SPEC (revamp plan R5).
//
// 2.0 slice 0.1 renamed two tab labels — Attendance became Calendar, KPI
// became Score — and stopped there. The tab said Calendar; the header at the
// top of the same screen still said Attendance. The app contradicted itself
// in two places for a whole release, and no test could notice because each
// half was internally consistent.
//
// So the invariant is the AGREEMENT, not either string: for every tab
// destination, the label in navItems.js and the pageTitle of the view it
// routes to must be the same word.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

//: The screen each tab destination renders. Hand-mapped rather than resolved
//: through the router, because the router builds these from constants and a
//: literal search cannot see through one — the same trap that made an earlier
//: guard report a route missing when it was present.
const TAB_SCREENS = {
	"/home": null, // Home's large title is "Today" (alpha.7), not the tab word
	"/dashboard/attendance": "views/attendance/Dashboard.vue",
	"/requests": "views/Requests.vue",
	"/dashboard/kpi": "views/kpi/Dashboard.vue",
}

function pageTitle(file) {
	const m = code(read(file)).match(/pageTitle="__\(['"]([^'"]*)['"]\)"/)
	return m ? m[1] : null
}

function navLabel(route) {
	const items = code(read("data/navItems.js"))
	// Each entry is `title: "X"` some lines above its `route: "/y"`. Match the
	// object, not the file, or every title matches every route.
	for (const block of items.split(/\n\t\{/)) {
		if (!block.includes(`route: "${route}"`) && !block.includes(`route: ${route}`)) continue
		const title = block.match(/title: "([^"]*)"/)
		if (title) return title[1]
	}
	return null
}

test("every tab's page header says the same word as its tab", () => {
	const disagreements = []
	for (const [route, file] of Object.entries(TAB_SCREENS)) {
		if (!file) continue
		const label = navLabel(route)
		const title = pageTitle(file)
		assert.ok(label, `${route} is in navItems.js`)
		assert.ok(title, `${file} has a pageTitle`)
		if (label !== title) disagreements.push(`${route}: tab says "${label}", page says "${title}"`)
	}
	assert.deepEqual(
		disagreements,
		[],
		"a tab and the screen it opens must not disagree about what the screen is"
	)
})

test("the retired words are gone from the screens that were renamed", () => {
	// Belt and braces on the two the plan named, so a future edit that renames
	// BOTH halves back does not quietly pass the agreement check above.
	assert.equal(pageTitle("views/attendance/Dashboard.vue"), "Calendar")
	assert.equal(pageTitle("views/kpi/Dashboard.vue"), "Score")
})
