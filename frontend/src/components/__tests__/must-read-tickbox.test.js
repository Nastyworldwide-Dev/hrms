// Owner, 19 Oct 2026: a must-read notice must be scrolled to the end AND a box ticked before it
// counts as read. Both places a must-read is confirmed carry the same tick: the full-screen
// notice on app open (MustReadNotice) and the notice opened from the board (Detail). The tick
// is disabled until the end is reached (utils/mustRead.js confirmState.canTick); the rule
// itself is utils/__tests__/mustRead.test.js. Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

for (const [name, path] of [
	["the full-screen must-read", "../MustReadNotice.vue"],
	["a notice opened from the board", "../../views/announcements/Detail.vue"],
]) {
	test(`${name} has the tick, open only once the end is reached`, () => {
		const src = read(path)
		assert.match(src, /<GCheckbox[\s\S]*?v-model="ticked"[\s\S]*?:disabled="!state\.canTick"/)
		assert.match(src, /__\(["']I have read and understood this["']\)/)
		assert.match(src, /confirmState\(\{[\s\S]*?ticked: ticked\.value/)
	})

	test(`${name} only records the read when the state is ready`, () => {
		const src = read(path)
		assert.match(src, /if \(!state\.value\.ready\)/)
	})
}

// Design review of a2f27ddb3: a disabled tick said "dimmed" with no reason, and the tick opening
// or Confirm turning ready was never announced. The tick points at the live line that says what
// is missing, in both places.
for (const path of ["../MustReadNotice.vue", "../../views/announcements/Detail.vue"]) {
	test(`${path}: the tick says why it is closed, and the change is announced`, () => {
		const src = read(path)
		// a fixed id, or one per notice where Ionic keeps the previous page (review of 808741bbc)
		const id = src.match(/:?described-by="([^"]+)"/)?.[1]
		assert.ok(id, "the tick names its reason")
		const escaped = id.replace(/[$`{}]/g, (c) => `\\${c}`)
		assert.match(src, new RegExp(`:?id="${escaped}" class="sr-only" aria-live="polite"`))
	})
}

// Review of a2f27ddb3: the board page must re-arm the end watch for EACH notice, once that
// notice's own text is shown; a short notice opened before a long one must not open its tick.
test("the board page re-arms the end watch per notice, on its own text", () => {
	const src = read("../../views/announcements/Detail.vue")
	assert.match(src, /doc\.value\?\.name === props\.id && entries\.some/)
	assert.match(src, /\(\) => \[endMarker\.value, doc\.value\?\.name === props\.id\]/)
})

test("the board page's live line is one per notice (Ionic keeps the last page in the DOM)", () => {
	const src = read("../../views/announcements/Detail.vue")
	assert.match(src, /:described-by="`announcement-confirm-\$\{id\}`"/)
	assert.match(src, /:id="`announcement-confirm-\$\{id\}`"/)
})

// Owner, 25 Oct 2026: tick + Confirm on the last must-read left a blank screen. `:can-dismiss="false"`
// made Ionic refuse the close that `is-open` going false asks for, so the empty modal stayed on top
// of the app. "Remind me later" on the last notice did the same. The modal may close once nothing
// is left to show, and never while a notice is on screen.
test("the full-screen must-read closes once no notice is left", () => {
	const src = read("../MustReadNotice.vue")
	assert.doesNotMatch(src, /:can-dismiss="false"/)
	assert.match(src, /:can-dismiss="allowClose"/)
	assert.match(src, /const allowClose = \(\) => !current\.value/)
})

// The gate's axe run, 25 Oct 2026: the notice text scrolls, but a keyboard could not reach it
// to scroll (scrollable-region-focusable, serious).
test("the full-screen notice text can be scrolled from a keyboard", () => {
	const src = read("../MustReadNotice.vue")
	assert.match(src, /ref="scroller"[\s\S]*?tabindex="0"[\s\S]*?role="region"[\s\S]*?:aria-label="__\('Notice text'\)"/)
})
