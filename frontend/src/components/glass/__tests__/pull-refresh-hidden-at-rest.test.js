// "Refreshing…" showed at the top of Home and "Pull to refresh" over Requests
// with nobody pulling (real phone, 23 Sep). The refresher sits above the page
// content, so its line must be hidden unless Ionic marks it active.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(
	fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)),
	"utf8"
)

test("the pull-to-refresh line is hidden unless the refresher is active", () => {
	assert.match(css, /ion-refresher:not\(\.refresher-active\) \.g-refresh \{\s*visibility: hidden;/)
})
