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
		const id = src.match(/described-by="([a-z-]+)"/)?.[1]
		assert.ok(id, "the tick names its reason")
		assert.match(src, new RegExp(`id="${id}" class="sr-only" aria-live="polite"`))
	})
}

// Review of a2f27ddb3: the board page must re-arm the end watch for EACH notice, once that
// notice's own text is shown; a short notice opened before a long one must not open its tick.
test("the board page re-arms the end watch per notice, on its own text", () => {
	const src = read("../../views/announcements/Detail.vue")
	assert.match(src, /doc\.value\?\.name === props\.id && entries\.some/)
	assert.match(src, /\(\) => \[endMarker\.value, doc\.value\?\.name === props\.id\]/)
})
