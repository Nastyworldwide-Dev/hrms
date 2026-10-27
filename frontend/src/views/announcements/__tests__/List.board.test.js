// The announcements board (owner-approved mockup, 27 Oct 2026): "To confirm · N" then "Latest",
// every row the Home vocabulary (red tile, summary under the title, Confirm / Urgent / New), and
// the age as a small caption on the right. The row rules themselves are run for real in
// utils/__tests__/announcementRow.test.js; this pins that the page draws them.
// Source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const raw = readFileSync(fileURLToPath(new URL("../List.vue", import.meta.url)), "utf8")
// comments blanked, so a comment that NAMES `__(category)` is not mistaken for code that calls it
const src = raw
	.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

test("two sections, 'To confirm · N' then 'Latest', each a titled panel", () => {
	assert.match(
		src,
		/<section v-for="group in groups" :key="group\.key" class="flex flex-col gap-2">/
	)
	assert.match(src, /<h2 class="g-eyebrow ml-4">\{\{ group\.title \}\}<\/h2>/)
	assert.match(src, /title: `\$\{__\("To confirm"\)\} · \$\{sections\.value\.toConfirm\.length\}`/)
	assert.match(src, /title: __\("Latest"\)/)
	assert.ok(src.indexOf('__("To confirm")') < src.indexOf('__("Latest")'), "to confirm leads")
	assert.doesNotMatch(src, /Everything else|Needs your confirmation/, "the old headings are gone")
	assert.match(
		src,
		/\.filter\(\(group\) => group\.rows\.length\)/,
		"an empty section draws nothing"
	)
})

test("the sections come from the one shared rule, not a second filter in the page", () => {
	assert.match(src, /import \{[^}]*boardSections[^}]*\} from "@\/utils\/announcementRow"/)
	assert.match(src, /boardSections\(rows\.value\)/)
	assert.doesNotMatch(src, /\.filter\(\(card\) => card\.needs_acknowledgement\)/)
})

test("each row is the Home row: red tile, category icon, title, summary", () => {
	assert.match(src, /import \{ TILE \} from "@\/utils\/iconTile"/)
	assert.equal((src.match(/<GListRow\b/g) || []).length, 1, "one row template for both sections")
	assert.match(src, /:tint="TILE\.announcement"/)
	assert.match(src, /:label="card\.title"/)
	assert.match(src, /:sublabel="subline\(card\)"/)
	assert.match(src, /<component :is="iconFor\(card\.category\)" class="g-row-icon" \/>/)
	assert.match(src, /const ICONS = \{/, "the category is mapped, not translated")
	assert.doesNotMatch(src, /__\(\s*\w*\.?category\s*[,)]/)
})

test("the badge is Confirm / Urgent / New by the shared rule, a word and never a bare dot", () => {
	assert.match(src, /import \{[^}]*badgeFor[^}]*\} from "@\/utils\/announcementRow"/)
	assert.match(src, /const badge = \(card\) => badgeFor\(card, __\)/)
	assert.match(
		src,
		/<span v-if="badge\(card\)\.variant === 'urgent'" class="g-badge g-chip--danger">/
	)
	assert.match(
		src,
		/<GBadge v-else :variant="badge\(card\)\.variant">\{\{ badge\(card\)\.text \}\}<\/GBadge>/
	)
	assert.doesNotMatch(
		src,
		/__\("Confirm"\)|__\("New"\)|__\("Urgent"\)/,
		"the words live in the shared util"
	)
	assert.doesNotMatch(src, /g-dot/)
})

test("the age is a small caption under the badge, right aligned", () => {
	assert.match(src, /import \{ siteTime \} from "@\/utils\/siteTime"/)
	assert.match(src, /const ageOf = \(date\) => siteTime\(date\)\.fromNow\(\)/)
	assert.match(src, /const age = \(card\) => trailAge\(card, __, ageOf\)/)
	assert.match(
		src,
		/<span\s+v-if="badge\(card\) \|\| age\(card\)"\s+class="flex flex-col items-end gap-0\.5 shrink-0"\s*>/
	)
	assert.match(
		src,
		/<span v-if="age\(card\)" class="text-caption text-ink-700 whitespace-nowrap">\{\{\s*age\(card\)\s*\}\}<\/span>/
	)
})

test("the empty state, the error and the loading panel are as before", () => {
	assert.match(src, /<ResourceError :resource="allAnnouncements" what="announcements" \/>/)
	assert.match(src, /<GEmptyState\s+v-if="!rows\.length && !allAnnouncements\.error"/)
	assert.match(src, /__\('Nothing on the board'\)/)
	assert.match(src, /<GListPanel v-if="allAnnouncements\.loading && !rows\.length" loading \/>/)
	assert.match(src, /<PushNudge \/>/)
})
