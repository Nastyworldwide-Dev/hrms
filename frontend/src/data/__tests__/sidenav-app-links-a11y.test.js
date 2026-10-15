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
// the app row is a <component> (an <a> for a sibling app, a router-link for a Nadi screen)
const anchor = src.slice(src.indexOf('v-for="item in appItems"'), src.indexOf("</component>", src.indexOf('v-for="item in appItems"')))

test("SideNav app anchors name themselves by title, not by the sublabel", () => {
	assert.ok(anchor.length > 0, "app anchors block must exist")
	assert.match(anchor, /:aria-label="item\.title"/)
	// a sibling app still opens in a new tab with noopener
	assert.match(anchor, /target: '_blank', rel: 'noopener'/)
})

// Amended 22 Sep 2026 (plan slice S4): `ExternalLinkIcon` was one of fourteen
// hand-rolled components that were Lucide glyphs pasted by hand; the package
// draws it now, as `<ExternalLink>`. The RULE is unchanged and is what this
// pins — the arrow is a decoration beside a named link, so it takes the muted
// ink token rather than competing with the label it sits next to.
test("SideNav app arrow glyph uses the same ink-3 token as More", () => {
	assert.match(anchor, /<ExternalLink[^>]*text-ink-3/)
})
