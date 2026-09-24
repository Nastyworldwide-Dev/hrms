// alpha.7 Phase 2 (plan §3): the forgotten check-out is a STATE of the Today
// card, not a separate warning banner (glass) stacked on it. One row inside
// the card: a warning glyph, what happened, what to do, a chevron.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../CheckInPanel.vue", import.meta.url)), "utf8")
const tpl = src.slice(src.indexOf("<template>"), src.indexOf("<script"))

test("the forgotten check-out is a row of the card, not a banner", () => {
	assert.doesNotMatch(tpl, /<GBanner/)
	assert.match(tpl, /v-if="hasStaleOpenIn"[\s\S]*class="g-today__issue/)
	assert.match(tpl, /@click="lateCheckoutOpen = true"/)
})
