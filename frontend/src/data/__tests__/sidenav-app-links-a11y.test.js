// The side nav's Apps anchors hide their label span when the rail is
// collapsed. Without an explicit aria-label the accessible-name algorithm
// falls back to `title`, which carries the sublabel — so Approva was announced
// as "Purchase requests & approvals". Pin the label on the anchor itself.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(
	fileURLToPath(new URL("../../components/SideNav.vue", import.meta.url)),
	"utf8"
)
const anchor = src.slice(src.indexOf('v-for="item in appItems"'), src.indexOf("</a>"))

test("SideNav app anchors name themselves by title, not by the sublabel", () => {
	assert.ok(anchor.length > 0, "app anchors block must exist")
	assert.match(anchor, /:aria-label="item\.title"/)
	assert.match(anchor, /rel="noopener"/)
})

test("SideNav app arrow glyph uses the same ink-3 token as More", () => {
	assert.match(anchor, /<ExternalLinkIcon[^>]*text-ink-3/)
})
