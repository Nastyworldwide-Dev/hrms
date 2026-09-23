// "Refreshing…" stuck after a pull (owner, after alpha.3). The flag waited for
// an ionRefreshComplete event Ionic 7 never sends (the refresher emits only
// ionRefresh, ionPull and ionStart), so after the first pull every later pull
// read "Refreshing…" from the first pixel. A new pull must start clean.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GPullRefresh.vue", import.meta.url)), "utf8")

test("every new pull starts as 'Pull to refresh'", () => {
	assert.match(src, /@ionStart="onStart"/)
	assert.match(src, /function onStart\(\) \{[^}]*refreshing\.value = false/)
})

test("it no longer waits for an event Ionic does not send", () => {
	assert.doesNotMatch(src, /ionRefreshComplete/)
})

// A page completes the pull after its reload. If the reload rejects or hangs,
// complete() never runs and the refresher stays open (Approvals awaited a
// reload that can reject). The component closes it itself after a cap.
test("a pull that nobody completes is closed after a cap", () => {
	assert.match(src, /const COMPLETE_CAP_MS = \d+/)
	assert.match(src, /setTimeout\(\(\) => event\.target\?\.complete\?\.\(\), COMPLETE_CAP_MS\)/)
})
