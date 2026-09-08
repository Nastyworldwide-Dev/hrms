// A foreground push notification must carry its destination on every browser.
//
// N07 (8 Sep 2026 notifications audit): App.vue routes foreground FCM messages
// through showNotification, which stored the URL on `data.url` only for Chrome
// and gave other browsers an action button instead. The worker's click handler
// resolves `data.url || event.action`; a BODY tap carries no action, so on
// Firefox/Safari/Samsung Internet a foreground notification opened nothing —
// the very defect the 2 Sep worker fix closed for background messages.
// Executes the real helper with a fake registration; no browser needed.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../pushNotifications.js", import.meta.url), "utf8")
const load = () =>
	new Function(`${source.replace(/export const /g, "const ")}\nreturn { showNotification, isChrome }`)()

function shown(userAgent, payload) {
	const calls = []
	globalThis.navigator = { userAgent }
	globalThis.window = {
		frappePushNotification: {
			serviceWorkerRegistration: { showNotification: (title, options) => calls.push({ title, options }) },
		},
	}
	load().showNotification(payload)
	return calls
}

const payload = {
	data: { title: "Leave approved", body: "Your leave was approved", click_action: "/hrms/leave-applications/HR-LAP-1" },
}

test("Firefox: a body tap can find the URL on data, and the action button stays", () => {
	const [call] = shown("Mozilla/5.0 (Android 14; Mobile; rv:128.0) Gecko/128.0 Firefox/128.0", payload)
	assert.equal(call.title, "Leave approved")
	assert.equal(call.options.data.url, "/hrms/leave-applications/HR-LAP-1")
	assert.deepEqual(call.options.actions, [{ action: "/hrms/leave-applications/HR-LAP-1", title: "View Details" }])
})

test("Chrome: the URL is on data and no action button is added", () => {
	const [call] = shown("Mozilla/5.0 (Linux; Android 14) Chrome/128.0 Mobile Safari/537.36", payload)
	assert.equal(call.options.data.url, "/hrms/leave-applications/HR-LAP-1")
	assert.equal(call.options.actions, undefined)
})

test("a message without a destination shows, with nowhere to go and no dead button", () => {
	const [call] = shown("Firefox/128.0", { data: { title: "Reminder", body: "Timesheet due" } })
	assert.equal(call.options.data.url, undefined)
	assert.equal(call.options.actions, undefined)
})

test("no registration yet: nothing is shown and nothing throws", () => {
	globalThis.navigator = { userAgent: "Firefox/128.0" }
	globalThis.window = { frappePushNotification: {} }
	assert.doesNotThrow(() => load().showNotification(payload))
})
