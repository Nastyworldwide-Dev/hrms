// Every push notification for a request opens that request (runtime crawl,
// 15 Sep 2026).
//
// hrms/hr/doctype/pwa_notification/pwa_notification.py builds the link a push
// carries. It mapped only Leave, Expense, Remote Checkin and Issue, so a tap
// on an OT Request, Shift Request or Replacement Leave Claim push landed on
// the PWA home — while the in-app feed (utils/notifications.js) derived
// `${Doctype}DetailView` and opened the request. Two sides of one contract,
// with nothing holding them together.
//
// This reads the backend's PWA_DETAIL_PATHS and resolves each against the
// real route table: every doctype with a derived DetailView route has a push
// link, and every push link is exactly that route's path.
import { test } from "node:test"
import assert from "node:assert/strict"
import { join } from "node:path"
import { createRouter, createMemoryHistory } from "vue-router"
import { HRMS_PY, read, routeTable } from "./_lib.mjs"

// DetailView routes that are not request doctypes a notification points at.
const NOT_NOTIFIED = {
	SopDetailView: "SOP library page, named for the feature, not a doctype",
}
// Doctypes that must never get a push link, with the ruling on record.
const HIDDEN = {
	"Employee Advance": "stays hidden in the PWA (owner ruling, 15 Sep 2026)",
}

const PY = join(HRMS_PY, "hr", "doctype", "pwa_notification", "pwa_notification.py")

function backendPaths() {
	const block = read(PY).match(/^PWA_DETAIL_PATHS\s*=\s*\{([\s\S]*?)^\}/m)
	assert.ok(block, "pwa_notification.py must declare PWA_DETAIL_PATHS = { doctype: path }")
	return Object.fromEntries(
		[...block[1].matchAll(/"([^"]+)"\s*:\s*"([^"]+)"/g)].map((m) => [m[1], m[2]])
	)
}

const { top, flat } = routeTable()
function toVueRoute(r) {
	const out = { path: r.path }
	if (r.name) out.name = r.name
	if (r.redirect) out.redirect = r.redirect.path ? { path: r.redirect.path } : r.redirect
	out.component = {}
	if (r.children) out.children = r.children.map(toVueRoute)
	return out
}
const router = createRouter({ history: createMemoryHistory(), routes: top.map(toVueRoute) })
const compact = (doctype) => `${doctype.replace(/\s+/g, "")}DetailView`

test("every doctype with a PWA DetailView route has a push notification link", () => {
	const paths = backendPaths()
	const linked = new Set(Object.keys(paths).map(compact))
	const missing = flat
		.filter((r) => r.name?.endsWith("DetailView") && !NOT_NOTIFIED[r.name])
		.filter((r) => !linked.has(r.name))
		.map((r) => r.name)
	assert.deepEqual(missing, [])
})

test("every push link is exactly its DetailView route's path", () => {
	const wrong = []
	for (const [doctype, path] of Object.entries(backendPaths())) {
		const name = compact(doctype)
		if (!router.hasRoute(name)) {
			wrong.push(`${doctype}: no ${name} route`)
			continue
		}
		const expected = router.resolve({ name, params: { id: "DOC-1" } }).path
		if (`/${path}/DOC-1` !== expected) wrong.push(`${doctype}: /${path}/:id, route is ${expected}`)
	}
	assert.deepEqual(wrong, [])
})

test("hidden doctypes never get a push link", () => {
	const paths = backendPaths()
	assert.deepEqual(
		Object.keys(HIDDEN).filter((doctype) => doctype in paths),
		[]
	)
})
