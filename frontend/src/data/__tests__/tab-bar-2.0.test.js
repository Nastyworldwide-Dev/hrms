// The tab bar the owner ruled for (2.0 slice 0.1, UX_PLAN Q1).
//
// HOME · CALENDAR · REQUESTS · SCORE · MORE, replacing Home · Attendance ·
// Leaves · Expenses · More. Ruled 22 Sep 2026: "follow as planned".
//
// Three of the five are RENAMES AND REROUTES, not new screens, and the plan
// says so in as many words: §3.2 "Calendar (today: Attendance)" and §3.6
// "Score screen is a reroute" over `/dashboard/kpi`. The fourth, Requests, is
// a hub the app does not have — today its contents are spread across the
// leave dashboard, the expense dashboard and the issues list.
//
// WHY THE TABS COME BEFORE HOME. The bar decides what Home is FOR: with a
// Requests tab, Home does not need to be a request list, and slice 1.3 would
// otherwise lay out a screen against a navigation that is about to change.
//
// WHAT MUST NOT BREAK. Every route the old tabs pointed at is a URL somebody
// has bookmarked, or that a push notification links to. Five fixed tabs also
// stay five: a bar whose destinations vary breaks Ionic's per-tab navigation
// stacks, which is why the count is fixed rather than "whatever fits".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function code(text) {
	return text
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

test("the bar is the five the owner named, in order", () => {
	const nav = code(read("data/navItems.js"))
	const block = nav.slice(nav.indexOf("export const TAB_ITEMS"), nav.indexOf("MORE_ITEMS"))
	// Four of the five are `NAV_ITEMS[n]` references, so their titles are not
	// in this block at all — resolve the index against NAV_ITEMS. Two earlier
	// versions of this read the comments (stripped, so never matched) and then
	// the literal titles (only More has one).
	const source = nav.slice(nav.indexOf("const NAV_ITEMS"), nav.indexOf("export const TAB_ITEMS"))
	const navTitles = [...source.matchAll(/title: "(\w+)"/g)].map((m) => m[1])
	const titles = [...block.matchAll(/NAV_ITEMS\[(\d)\]|title: "(\w+)"/g)].map((m) =>
		m[1] === undefined ? m[2] : navTitles[Number(m[1])]
	)
	assert.deepEqual(
		titles,
		["Home", "Calendar", "Requests", "Score", "More"],
		"Home · Calendar · Requests · Score · More (UX_PLAN Q1)"
	)
})

test("still exactly five", () => {
	const nav = code(read("data/navItems.js"))
	const block = nav.slice(nav.indexOf("export const TAB_ITEMS"), nav.indexOf("MORE_ITEMS"))
	// Count the entries, not the lines: a bar whose destinations vary breaks
	// Ionic's per-tab stacks.
	const entries = (block.match(/NAV_ITEMS\[\d\]|\{\s*$/gm) || []).length
	assert.equal(entries, 5, "five fixed destinations")
})

test("Calendar and Score are the screens that already exist", () => {
	// §3.2 "Calendar (today: Attendance)"; §3.6 "Score screen is a reroute".
	// Renaming a tab must not orphan the screen behind it.
	const nav = code(read("data/navItems.js"))
	const calendar = nav.slice(
		nav.indexOf('title: "Calendar"'),
		nav.indexOf('title: "Calendar"') + 200
	)
	assert.match(calendar, /\/dashboard\/attendance/, "Calendar is the attendance screen, renamed")
	const score = nav.slice(nav.indexOf('title: "Score"'), nav.indexOf('title: "Score"') + 200)
	assert.match(score, /\/dashboard\/kpi/, "Score is the KPI screen, renamed")
})

test("Requests has a route, and the router serves it", () => {
	const nav = code(read("data/navItems.js"))
	const requests = nav.slice(
		nav.indexOf('title: "Requests"'),
		nav.indexOf('title: "Requests"') + 200
	)
	const route = requests.match(/route: "([^"]+)"/)
	assert.ok(route, "the Requests tab names a route")
	const router = code(readFileSync(join(SRC, "router/index.js"), "utf8"))
	assert.match(
		router,
		new RegExp(`path: "${route[1]}"`),
		`${route[1]} must be a real route, or the tab is a dead end`
	)
})

test("every old tab route still resolves", () => {
	// `/dashboard/leaves` and `/dashboard/expense-claims` lose their tab. They
	// do NOT lose their URL: those are bookmarks, and push notifications link
	// to them.
	const router = code(readFileSync(join(SRC, "router/index.js"), "utf8"))
	for (const path of [
		"/home",
		"/dashboard/attendance",
		"/dashboard/leaves",
		"/dashboard/expense-claims",
		"/dashboard/kpi",
	]) {
		assert.match(router, new RegExp(`path: "${path}"`), `${path} was a tab; it stays a URL`)
	}
})

test("what left the bar is reachable from More", () => {
	// Leaves and Expenses are not gone, they are one tap further away. A
	// destination with no tab and no More row is a screen nobody can reach.
	const nav = code(read("data/navItems.js"))
	assert.match(nav, /MORE_ITEMS/, "More still lists the rest")
	const more = nav.slice(nav.indexOf("export const MORE_ITEMS"))
	assert.match(more, /dashboard\/leaves|NAV_ITEMS/, "and the list includes what the bar dropped")
})

test("the More tab claims the routes it now owns", () => {
	// More's `routes` array drives its active state. A destination that moved
	// under More without being listed leaves the bar showing nothing selected.
	const nav = code(read("data/navItems.js"))
	const more = nav.slice(nav.indexOf('title: "More"'))
	const routes = more.slice(more.indexOf("routes:"), more.indexOf("]", more.indexOf("routes:")))
	for (const path of ["/dashboard/leaves", "/dashboard/expense-claims"]) {
		assert.match(routes, new RegExp(path), `${path} lives under More now; it must light More up`)
	}
})
