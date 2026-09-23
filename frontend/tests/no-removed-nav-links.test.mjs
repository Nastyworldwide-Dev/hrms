// Issues and Helpdesk are ONE sidebar entry now (15 Sep 2026). The two old
// list routes survive only as redirects in router/helpdeskHub.js; nothing else
// may still point at them — a view that does would resolve through a
// redirect today and 404 the day the redirect is retired.
import test from "node:test"
import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const src = fileURLToPath(new URL("../src", import.meta.url))

const walk = (dir, out = []) => {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__") walk(path, out)
		} else if (/\.(vue|js)$/.test(entry) && !/\.test\./.test(entry))
			out.push(path)
	}
	return out
}

// the redirect table is the ONE place the old paths are allowed to appear
const allowed = new Set([join(src, "router", "helpdeskHub.js")])

const files = walk(src).filter((f) => !allowed.has(f))

const removed = [
	// old list paths as navigation targets (a form child like "/issues/new" is fine)
	/["'`]\/issues["'`]/,
	/["'`]\/helpdesk["'`]/,
	/["'`]\/hr\/issues["'`]/,
	// old list route names
	/EmployeeIssueListView/,
	/["']HelpdeskList["']/,
	// the separate nav entry that used to be appended behind the availability gate
	/HELPDESK_ITEM/,
]

test("no view, component or data module still links to the removed Issues/Helpdesk entries", () => {
	const offenders = []
	for (const file of files) {
		const text = readFileSync(file, "utf8")
		for (const pattern of removed) {
			if (pattern.test(text))
				offenders.push(`${file.slice(src.length + 1)} matches ${pattern}`)
		}
	}
	assert.deepEqual(offenders, [])
})

test("the sidebar has exactly one Helpdesk entry, where Issues used to sit", () => {
	const nav = readFileSync(join(src, "data", "navItems.js"), "utf8")
	const titles = [...nav.matchAll(/title: "([^"]+)"/g)].map((m) => m[1])
	// Amended 22 Sep 2026 (2.0 slice 0.1). This listed the pre-2.0 titles, so
	// it failed on the rename it was never about: Attendance -> Calendar,
	// KPI -> Score, plus the new Requests hub. What it EXISTS for is the
	// Helpdesk consolidation — one entry, where Issues used to sit — and that
	// is what it asserts now. Pinning every title made this test a second
	// definition of the nav, which is how a rename becomes a failure nobody
	// reads.
	assert.equal(
		// "Help" since 23 Sep 2026 (audit-pages §4, W-PLAIN).
		titles.filter((t) => t === "Help").length,
		1,
		"exactly one Help entry"
	)
	assert.equal(titles[0], "Home", "Home is still first")
	assert.equal(titles.at(-1), "More", "More is still last")
	// The consolidation put Helpdesk in the slot Issues held: after SOPs' two
	// neighbours, before More.
	assert.ok(
		titles.indexOf("Help") < titles.indexOf("SOPs"),
		"in the slot Issues held"
	)
	assert.ok(!titles.includes("Issues"))
	assert.match(nav, /title: "Help",[\s\S]*?route: HUB_PATH/)
})
