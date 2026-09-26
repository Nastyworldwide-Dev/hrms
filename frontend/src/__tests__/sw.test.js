// The service worker's notificationclick handler used to be registered only
// inside if(isChrome()), so on Firefox/Safari/Samsung Internet tapping a push
// notification opened nothing. Source-asserted (a service worker can't be run
// under node — it needs self/clients/registration), the same way the SFC tests
// pin behaviour they can't execute. This guards against the handler being
// re-gated behind a browser check.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../../public/sw.js", import.meta.url)), "utf8")

test("notificationclick is registered for every browser, not only Chrome", () => {
	const idx = src.indexOf('addEventListener("notificationclick"')
	assert.ok(idx > 0, "a notificationclick handler exists")
	// the 200 chars before the handler must NOT open an isChrome() gate that
	// wraps it (the bug was `if (isChrome()) { addEventListener(...) }`).
	const before = src.slice(Math.max(0, idx - 200), idx)
	assert.doesNotMatch(
		before,
		/if\s*\(\s*isChrome\(\)\s*\)\s*\{\s*$/,
		"handler must not be gated behind isChrome()"
	)
})

test("the click handler resolves the URL from data OR the action button", () => {
	assert.match(
		src,
		/event\.notification\.data && event\.notification\.data\.url\) \|\| event\.action/,
		"must read data.url (body tap) or event.action (non-Chrome action button)"
	)
})

test("the notification URL is stored on data for every browser", () => {
	// data.url must be set unconditionally, not only in the isChrome branch.
	const dataIdx = src.indexOf('notificationOptions["data"]')
	const chromeIdx = src.indexOf("if (isChrome())")
	assert.ok(
		dataIdx > 0 && (chromeIdx < 0 || dataIdx < chromeIdx),
		"data.url set before/without the isChrome branch"
	)
})

// alpha.12 C1: the installed app opened offline to a browser error. The app's
// page is rendered per user by Frappe (it carries the CSRF token and boot), so
// it is not in the build's precache. The worker keeps the last good copy of
// each /hrms page, network first, and serves it when the network is gone.
test("an /hrms page is served network-first with an offline fallback", () => {
	assert.match(src, /from "workbox-routing"/)
	assert.match(src, /from "workbox-strategies"/)
	assert.match(src, /new NavigationRoute\(/)
	assert.match(src, /new NetworkFirst\(/)
	assert.match(src, /allowlist:\s*\[\s*\/\^\\\/hrms/)
})

// alpha.12 C1, review of 6a1f33315 (REFUTED by a fresh verifier): the build's
// precache entries are RELATIVE ("assets/x.js"). Workbox resolves them against
// the worker's own URL — now /hrms/sw.js — so they became /hrms/assets/x.js,
// which Frappe's /hrms catch-all answers with the app's HTML. The worker cached
// 176 HTML pages under asset names and none of the real files; offline launch
// was blank once the browser's HTTP cache was gone. Entries are re-based onto
// the build's real home before precaching.
test("precache entries are re-based onto /assets/hrms/frontend/", () => {
	assert.match(src, /const ASSET_BASE = "\/assets\/hrms\/frontend\/"/)
	assert.match(src, /precacheAndRoute\(rebased\(self\.__WB_MANIFEST\)\)/)
})

test("the re-base rule, run: relative entries move, absolute ones stay", () => {
	const start = src.indexOf("function rebased(")
	const body = src.slice(start, src.indexOf("\n}\n", start) + 2)
	const ASSET_BASE = "/assets/hrms/frontend/"
	const rebased = new Function("ASSET_BASE", `${body}; return rebased`)(ASSET_BASE)
	assert.deepEqual(
		rebased([{ url: "assets/a.js", revision: null }, "index.html", { url: "/x.png", revision: "1" }]),
		[
			{ url: "/assets/hrms/frontend/assets/a.js", revision: null },
			{ url: "/assets/hrms/frontend/index.html", revision: null },
			{ url: "/x.png", revision: "1" },
		]
	)
})

// Review of 6a1f33315: phones installed before alpha.12 keep the old worker
// (scope /assets/hrms/frontend/) and a push token tied to it.
const main = readFileSync(fileURLToPath(new URL("../main.js", import.meta.url)), "utf8")

test("the pre-alpha.12 worker is retired once the app-root worker registers", () => {
	assert.match(main, /const OLD_WORKER_SCOPE = "\/assets\/hrms\/frontend\/"/)
	assert.match(main, /getRegistrations\(\)/)
	assert.match(main, /\.unregister\(\)/)
	const then = main.slice(main.indexOf(".then((registration) => {"))
	assert.ok(then.indexOf("retireOldWorker()") > 0 && then.indexOf("retireOldWorker()") < then.indexOf(".catch("))
})

test("push moves to the app-root worker once, only for people who had it on", () => {
	const fn = main.slice(main.indexOf("async function movePushToAppWorker"))
	assert.match(fn, /isNotificationEnabled\?\.\(\)/)
	assert.match(fn, /Notification\.permission !== "granted"/)
	assert.match(fn, /localStorage\.getItem\(PUSH_MOVED_KEY\)/)
	assert.match(fn, /enableNotification\(\)/)
})
