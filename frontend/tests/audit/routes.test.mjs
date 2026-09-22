// Route table integrity (static audit, 15 Sep 2026).
//
// Every navigation the PWA can perform is a string somewhere in src/ — a route
// name in router.push({ name }), a :to on a RouterLink, a `route:` path in the
// sidebar / tab bar / More / QuickLinks tables, a DetailView name DERIVED from
// a doctype. Nothing type-checks those strings, and a link to a removed route
// renders a control that does nothing (the "Issues" entry after the Helpdesk
// merge; RemoteCheckinRequestDetailView from a notification tap).
//
// This resolves every one of them against the real table with a real
// vue-router instance, and checks the table itself: every component file
// exists and is a component, every redirect lands, no two routes share a name.
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync } from "node:fs"
import { createRouter, createMemoryHistory } from "vue-router"
import {
	SRC,
	read,
	rel,
	routeTable,
	resolveImport,
	sourceFiles,
	sfc,
	templateText,
	scriptText,
} from "./_lib.mjs"

const { top, flat } = routeTable()
const named = flat.filter((r) => r.name)
const names = new Set(named.map((r) => r.name))

// A real router built from the parsed table — dummy components, real matching.
function toVueRoute(r) {
	const out = { path: r.path }
	if (r.name) out.name = r.name
	if (r.redirect)
		out.redirect = r.redirect.path ? { path: r.redirect.path } : r.redirect
	if (r.component) out.component = { name: r.component }
	if (r.children) out.children = r.children.map(toVueRoute)
	if (!out.component && !out.redirect && !out.children) out.component = {}
	return out
}
const router = createRouter({
	history: createMemoryHistory(),
	routes: top.map(toVueRoute),
})

const resolves = (target) => {
	const resolved = router.resolve(target)
	return resolved.matched.length > 0 && resolved.name !== "NotFound"
}

test("every routed component file exists and is a Vue component", () => {
	const missing = []
	for (const r of flat) {
		if (!r.component) continue
		const path = resolveImport(r.component, SRC)
		if (!existsSync(path)) {
			missing.push(`${r.path} → ${r.component} (file missing)`)
			continue
		}
		const { descriptor } = sfc(path)
		if (!descriptor.template && !descriptor.scriptSetup && !descriptor.script)
			missing.push(`${r.path} → ${r.component} (not a component)`)
	}
	assert.deepEqual(missing, [])
})

test("no two routes share a name", () => {
	const seen = new Map()
	const dupes = []
	for (const r of named) {
		if (seen.has(r.name))
			dupes.push(`${r.name}: ${seen.get(r.name)} and ${r.path}`)
		seen.set(r.name, r.path)
	}
	assert.deepEqual(dupes, [])
})

test("every redirect lands on a real route", () => {
	const dead = []
	for (const r of flat) {
		if (!r.redirect) continue
		const target = typeof r.redirect === "string" ? r.redirect : r.redirect
		if (target.name && !names.has(target.name))
			dead.push(`${r.path} → name ${target.name}`)
		else if (
			!resolves(target.name ? { name: target.name } : target.path || target)
		)
			dead.push(`${r.path} → ${JSON.stringify(target)}`)
	}
	assert.deepEqual(dead, [])
})

// Route NAMES referenced anywhere in src/ (outside the router itself):
//   { name: "X" } / name: 'X'      router.push / :to objects
//   route: "X"                      Home.vue quick links (PascalCase = a name)
//   hasRoute("X") / .name === "X"   guards and comparisons
const NAME_RE =
	/(?:\bname\s*:\s*|\broute\s*:\s*|hasRoute\(\s*|\.name\s*===?\s*)["']([A-Z][A-Za-z]+)["']/g
// Identifiers that look like route names but are not navigation (component
// registrations, doctype names never match — they carry spaces).
const NOT_ROUTES = new Set(["GTag", "Expenses"])

test("every route name referenced in src/ is registered", () => {
	const offenders = []
	for (const file of sourceFiles()) {
		if (file.includes("/src/router/")) continue
		const text = read(file)
		for (const m of text.matchAll(NAME_RE)) {
			const name = m[1]
			if (NOT_ROUTES.has(name) || names.has(name)) continue
			const line = text.slice(0, m.index).split("\n").length
			offenders.push(`${rel(file)}:${line} → ${name}`)
		}
	}
	assert.deepEqual(offenders, [])
})

// Constants imported from utils/helpdeskHub.js are route names too.
test("HUB_ROUTE_NAME is a registered route", () => {
	const text = read(`${SRC}/utils/helpdeskHub.js`)
	const name = text.match(/HUB_ROUTE_NAME = "(\w+)"/)[1]
	assert.ok(names.has(name), name)
})

// DERIVED names: FormView, ListView, RequestActionSheet and the notification
// router build `${Doctype}DetailView` / `${Doctype}FormView` from a doctype.
// Every doctype that reaches those components must have the derived route —
// except the two read-only lists, which guard the "New" button themselves
// (ListView.canCreate), and Employee Checkin, whose rows open a modal
// (ListView.vue `v-if="props.doctype === 'Employee Checkin'"`) not a route.
const READ_ONLY_LISTS = new Set(["Employee Checkin", "Shift Assignment"])
const MODAL_LISTS = new Set(["Employee Checkin"])

test("every doctype rendered by FormView has a DetailView route", () => {
	const missing = []
	for (const file of sourceFiles()) {
		if (!file.endsWith(".vue")) continue
		const tpl = templateText(file)
		for (const m of tpl.matchAll(/<FormView[\s\S]*?doctype="([^"]+)"/g)) {
			const name = `${m[1].replace(/\s+/g, "")}DetailView`
			if (!names.has(name)) missing.push(`${rel(file)}: ${m[1]} → ${name}`)
		}
	}
	assert.deepEqual(missing, [])
})

test("every doctype rendered by ListView has DetailView and (unless read-only) FormView routes", () => {
	const missing = []
	for (const file of sourceFiles()) {
		if (!file.endsWith(".vue")) continue
		const tpl = templateText(file)
		for (const m of tpl.matchAll(/<ListView[\s\S]*?doctype="([^"]+)"/g)) {
			const base = m[1].replace(/\s+/g, "")
			if (!MODAL_LISTS.has(m[1]) && !names.has(`${base}DetailView`))
				missing.push(`${rel(file)}: ${m[1]} → ${base}DetailView`)
			if (!READ_ONLY_LISTS.has(m[1]) && !names.has(`${base}FormView`))
				missing.push(`${rel(file)}: ${m[1]} → ${base}FormView`)
		}
	}
	assert.deepEqual(missing, [])
})

// PATH links: `route: "/x"` in navItems / More / SideNav, router.push("/x"),
// to="/x". Each must resolve to something other than NotFound.
const PATH_RE =
	/(?:\broute\s*:\s*|router\.(?:push|replace)\(\s*|(?<![:\w])to=)["'`](\/[^"'`]*)["'`]/g

test("every sidebar, tab-bar, More and QuickLinks path resolves", () => {
	const dead = []
	for (const file of sourceFiles()) {
		if (file.includes("/src/router/")) continue
		const text = read(file)
		for (const m of text.matchAll(PATH_RE)) {
			const path = m[1]
			if (!resolves(path)) {
				const line = text.slice(0, m.index).split("\n").length
				dead.push(`${rel(file)}:${line} → ${path}`)
			}
		}
	}
	assert.deepEqual(dead, [])
})

// The one place a navigation target is data rather than code: the nav tables.
test("navItems tab bar and More entries all resolve", async () => {
	const text = read(`${SRC}/data/navItems.js`)
	const dead = []
	for (const m of text.matchAll(/route:\s*(\w+|"[^"]+")/g)) {
		const raw = m[1].replace(/"/g, "")
		const path = raw.startsWith("/")
			? raw
			: read(`${SRC}/utils/helpdeskHub.js`).match(
					new RegExp(`${raw} = "([^"]+)"`)
			  )?.[1]
		if (!path || !resolves(path)) dead.push(`navItems.js → ${raw}`)
	}
	assert.deepEqual(dead, [])
})

// Views are the unit of routing: a view file that no route and no other view
// imports is a dead page (never reachable).
test("every file under views/ is routed or imported by a routed view", () => {
	const routed = new Set(
		flat.filter((r) => r.component).map((r) => resolveImport(r.component, SRC))
	)
	const imported = new Set()
	for (const file of sourceFiles()) {
		for (const spec of file.endsWith(".vue") || file.endsWith(".js")
			? importsFrom(file)
			: []) {
			const target = resolveImport(spec, file)
			if (target) imported.add(target)
		}
	}
	const dead = sourceFiles(`${SRC}/views`)
		.filter((f) => f.endsWith(".vue"))
		.filter((f) => !routed.has(f) && !imported.has(f))
		.map(rel)
	assert.deepEqual(dead, [])
})

function importsFrom(file) {
	const text = file.endsWith(".vue") ? scriptText(file) : read(file)
	return [
		...text.matchAll(
			/\bimport\s*(?:[\w${},*\s]+?\s*from\s*)?["']([^"']+)["']|\bimport\(\s*["']([^"']+)["']\s*\)/g
		),
	].map((m) => m[1] || m[2])
}
