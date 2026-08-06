// Tests for the push-notification auto-prompt decision logic (v15.104.0).
// The PWA shows a soft-ask sheet on open; these cover the eligibility gate and
// the per-device decline flag. Run with: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"

import {
	DECLINE_KEY,
	escalatesOnDismiss,
	hasDeclined,
	recordDecline,
	shouldShowPushPrompt,
} from "../src/utils/pushPrompt.js"

const mockStorage = () => {
	const map = new Map()
	return {
		getItem: (k) => (map.has(k) ? map.get(k) : null),
		setItem: (k, v) => map.set(k, String(v)),
		removeItem: (k) => map.delete(k),
	}
}

const eligibleCtx = (overrides = {}) => ({
	relayConfigured: true,
	siteEnabled: true,
	alreadyEnabled: false,
	notificationSupported: true,
	browserPermission: "default",
	declined: false,
	sdkInitialized: true,
	...overrides,
})

test("shows when every gate condition holds", () => {
	assert.equal(shouldShowPushPrompt(eligibleCtx()), true)
})

test("each blocking condition alone hides the prompt", () => {
	const blockers = [
		{ relayConfigured: false },
		{ siteEnabled: false },
		{ alreadyEnabled: true },
		{ notificationSupported: false },
		{ browserPermission: "denied" },
		{ declined: true },
		{ sdkInitialized: false },
	]
	for (const override of blockers) {
		assert.equal(
			shouldShowPushPrompt(eligibleCtx(override)),
			false,
			`expected hidden for ${JSON.stringify(override)}`
		)
	}
})

test("permission already granted but no token still shows (silent re-enable)", () => {
	// e.g. user cleared site data: browser permission survives, FCM token doesn't
	assert.equal(
		shouldShowPushPrompt(eligibleCtx({ browserPermission: "granted" })),
		true
	)
})

test("decline flag round-trips through storage under DECLINE_KEY", () => {
	const storage = mockStorage()
	assert.equal(hasDeclined(storage), false)
	recordDecline(storage)
	assert.equal(hasDeclined(storage), true)
	assert.ok(storage.getItem(DECLINE_KEY) !== null)
})

test("swipe-away of the soft ask escalates to the confirm step, once", () => {
	assert.equal(escalatesOnDismiss(1, false), true)
	// confirm step swiped away → no escalation, no decline recorded
	assert.equal(escalatesOnDismiss(2, false), false)
	// an answered sheet (enabled, blocked, or declined) never reopens
	assert.equal(escalatesOnDismiss(1, true), false)
	assert.equal(escalatesOnDismiss(2, true), false)
})

test("recorded decline blocks the prompt", () => {
	const storage = mockStorage()
	recordDecline(storage)
	assert.equal(
		shouldShowPushPrompt(eligibleCtx({ declined: hasDeclined(storage) })),
		false
	)
})
