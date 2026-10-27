// 27 Oct 2026 (owner: "cache related stuff on notification"). The bell count
// and the feed were refreshed only by the socket's hrms:refetch_resource. A
// phone that put the app away misses that event for good (the server replays
// nothing), so the bell and the cached feed stayed as they were until a full
// reload. Both now reload on the app's one "events may have been missed" hook
// (composables/realtime.useReloadOnGap: a reconnect, or back after a long hide).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../notifications.js", import.meta.url)), "utf8")

test("the bell and the feed catch up after a gap the socket could not cover", () => {
	assert.match(src, /import \{ useReloadOnGap \} from "@\/composables\/realtime"/)
	const hook = src.slice(src.indexOf("useReloadOnGap("))
	assert.match(hook, /refreshNotifications/)
	assert.match(src, /unreadNotificationsCount\.reload\(\)/)
	// the feed only when a page of it was ever asked for: a list never fetched
	// has nothing stale, and fetching it here would load it on every screen
	assert.match(src, /if \(notifications\.list\.fetched\) notifications\.reload\(\)/)
})

test("a push that lands while the app is open refreshes the bell and the feed", () => {
	const app = readFileSync(fileURLToPath(new URL("../../App.vue", import.meta.url)), "utf8")
	const handler = app.slice(app.indexOf("frappePushNotification?.onMessage"))
	assert.match(handler, /showNotification\(payload\)/)
	assert.match(handler, /refreshNotifications\("push while open"\)/)
	assert.match(src, /export function refreshNotifications\(/)
})

test("a signed-out page does not ask for notifications when it comes back", () => {
	const body = src.slice(src.indexOf("export function refreshNotifications("))
	assert.match(body, /if \(!sessionUser\(\)\) return/)
})
