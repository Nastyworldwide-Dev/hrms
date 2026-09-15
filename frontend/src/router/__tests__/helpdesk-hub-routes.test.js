// Issues and Helpdesk merged into ONE tab-shell page (15 Sep 2026). The old
// list URLs must keep working as redirects into the right pill — a push
// notification, a bookmark or the v15.105.0 quick link must never 404 — while
// the form/detail children stay where they were.
//
// router/index.js imports TabbedView.vue statically, so the table is proved two
// ways: the Vue-free redirect rows through a real vue-router, and index.js as
// source for where they are spliced in.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { createRouter, createMemoryHistory } from "vue-router"

import { HUB_PATH, HUB_ROUTE_NAME } from "../../utils/helpdeskHub.js"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")

// "@/…" is a Vite alias; rewrite it so node can load the module unchanged
const load = async (rel) => {
	const src = read(rel).replace(
		/from "@\/utils\/helpdeskHub"/,
		`from "${new URL("../../utils/helpdeskHub.js", import.meta.url).href}"`
	)
	const url = "data:text/javascript;base64," + Buffer.from(src).toString("base64")
	return (await import(url)).default
}

const table = async () => {
	const redirects = await load("../helpdeskHub.js")
	const issueRoutes = (await import("../issues.js")).default
	const helpdeskRoutes = (await import("../helpdesk.js")).default
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: HUB_PATH, name: HUB_ROUTE_NAME, component: {} },
			...redirects,
			{ path: "/form", component: {}, children: [...issueRoutes, ...helpdeskRoutes] },
			{ path: "/:pathMatch(.*)*", name: "NotFound", component: {} },
		],
	})
}

// redirects are followed by a NAVIGATION, not by resolve()
const go = async (router, path) => {
	await router.push(path)
	return router.currentRoute.value
}

test("old /issues opens the hub on the HR Issues pill", async () => {
	const to = await go(await table(), "/issues")
	assert.equal(to.name, HUB_ROUTE_NAME)
	assert.equal(to.path, HUB_PATH)
	assert.equal(to.query.tab, "hr")
})

test("old /helpdesk opens the hub on the IT Helpdesk pill", async () => {
	const to = await go(await table(), "/helpdesk")
	assert.equal(to.name, HUB_ROUTE_NAME)
	assert.equal(to.query.tab, "it")
})

test("the v15.105.0 /hr/issues alias still lands on HR Issues, not NotFound", async () => {
	const to = await go(await table(), "/hr/issues")
	assert.equal(to.name, HUB_ROUTE_NAME)
	assert.equal(to.query.tab, "hr")
})

test("form and detail children are untouched by the redirects", async () => {
	const router = await table()
	assert.equal(router.resolve("/issues/new").name, "EmployeeIssueFormView")
	assert.equal(router.resolve("/issues/HR-ISS-26-09-00001").name, "EmployeeIssueDetailView")
	assert.equal(router.resolve("/helpdesk/new").name, "HelpdeskTicketNew")
	assert.equal(router.resolve("/helpdesk/42").name, "HelpdeskTicketDetail")
})

test("a bare hub visit carries no pill — the view resolves it (memory, then hr)", async () => {
	const router = await table()
	const to = router.resolve(HUB_PATH)
	assert.equal(to.name, HUB_ROUTE_NAME)
	assert.equal(to.query.tab, undefined)
})

test("index.js mounts the hub in the tab shell and splices the redirects beside it", () => {
	const source = read("../index.js")
	assert.match(source, /import helpdeskHubRoutes from "\.\/helpdeskHub"/)
	const shell = source.slice(
		source.indexOf("component: TabbedView"),
		source.indexOf('path: "/login"')
	)
	assert.match(shell, /\.\.\.helpdeskHubRoutes/, "redirects live in the tab shell")
	assert.match(
		shell,
		/path: HUB_PATH,\s*name: HUB_ROUTE_NAME,\s*component: \(\) => import\("@\/views\/helpdesk\/HelpdeskHub\.vue"\)/
	)
	assert.ok(!/path: "\/issues",\s*name/.test(shell), "the old Issues list route is gone")
	assert.ok(!/HelpdeskList\.vue/.test(shell), "the old Helpdesk list route is gone")
	// the legacy alias moved out of issues.js with the other redirects
	assert.ok(!/\/hr\/issues/.test(read("../issues.js")))
})
