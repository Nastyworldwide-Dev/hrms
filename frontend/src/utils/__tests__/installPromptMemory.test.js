// The PWA install sheet overlays the tab bar, and beforeinstallprompt fires on
// every load — so before this guard existed the sheet re-covered the navigation
// on every cold start. isWithinCooldown is what keeps it quiet after a
// dismissal; if it ever returns false for a fresh dismissal the nag comes back,
// and if it returns true forever the user can never re-summon the prompt.
import { test } from "node:test"
import assert from "node:assert/strict"

import { isWithinCooldown, INSTALL_COOLDOWN_MS } from "../installPromptMemory.js"

const NOW = 1_700_000_000_000

test("a fresh dismissal suppresses the prompt", () => {
	assert.equal(isWithinCooldown(NOW, NOW), true)
	assert.equal(isWithinCooldown(NOW - 1000, NOW), true, "dismissed a second ago")
	assert.equal(
		isWithinCooldown(NOW - (INSTALL_COOLDOWN_MS - 1), NOW),
		true,
		"just inside cooldown"
	)
})

test("the prompt returns once the cooldown lapses", () => {
	assert.equal(isWithinCooldown(NOW - INSTALL_COOLDOWN_MS, NOW), false, "exactly at the edge")
	assert.equal(isWithinCooldown(NOW - 2 * INSTALL_COOLDOWN_MS, NOW), false, "long past")
})

test("absent or junk storage never suppresses — the prompt is allowed to show", () => {
	assert.equal(isWithinCooldown(null, NOW), false)
	assert.equal(isWithinCooldown("", NOW), false)
	assert.equal(isWithinCooldown("not-a-number", NOW), false)
	assert.equal(isWithinCooldown("0", NOW), false)
	// A future timestamp (clock skew) is treated as not-suppressed, not forever-on.
	assert.equal(isWithinCooldown(NOW + 5000, NOW), false)
})

// alpha.7 0.10: on iPhone Safari the hint was a lime popover over the bottom
// of EVERY page (contrast 1.18). It is now one row on Home, and this rule is
// the only thing that decides whether that row shows.
import { showIosInstallHint } from "../installPromptMemory.js"

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"
const hint = (o = {}) =>
	showIosInstallHint({ userAgent: IPHONE, standalone: false, stored: null, now: NOW, ...o })

test("iPhone Safari, not installed, never dismissed: the hint shows", () => {
	assert.equal(hint(), true)
})

test("installed, dismissed within 30 days, or not an iPhone: no hint", () => {
	assert.equal(hint({ standalone: true }), false, "already on the Home Screen")
	assert.equal(hint({ stored: String(NOW - 1000) }), false, "closed a second ago")
	assert.equal(hint({ userAgent: "Mozilla/5.0 (Linux; Android 14) Chrome/128" }), false)
	assert.equal(hint({ stored: String(NOW - INSTALL_COOLDOWN_MS) }), true, "30 days later it may show once more")
})
