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
