// A tapped notification must be marked read through a method staff may call.
//
// Notifications.vue marked a tapped row read with the list resource's
// setValue — frappe.client.set_value on PWA Notification. Staff hold READ on
// that doctype and nothing else, so every tap 403'd: a "Could not load — Not
// permitted" toast over whatever the tap had opened, an uncaught page error,
// and an unread count that only ever grew. Source-level pin, like the other
// tests in this directory: the screen must call the scoped endpoint and must
// not write the doctype directly.
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const here = dirname(fileURLToPath(import.meta.url))
const view = readFileSync(join(here, "../src/views/Notifications.vue"), "utf8")

test("marking one notification read goes through hrms.api.mark_notification_as_read", () => {
	assert.match(
		view,
		/hrms\.api\.mark_notification_as_read/,
		"Notifications.vue must mark a tapped row read via the whitelisted, to_user-scoped method"
	)
})

test("the screen never writes PWA Notification through setValue", () => {
	assert.doesNotMatch(
		view,
		/notifications\.setValue/,
		"frappe.client.set_value on PWA Notification is a 403 for staff — do not reintroduce it"
	)
})
