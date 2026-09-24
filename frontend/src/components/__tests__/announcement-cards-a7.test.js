// alpha.7 §10.1/§10.2: a Home card is the title, HR's Summary (not text cut
// from the body), and the cover as a small thumbnail when there is one;
// the red announcement tile otherwise. Must-read waits with a word.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Announcements.vue", import.meta.url)), "utf8")

test("the preview line is HR's summary", () => {
	assert.match(src, /card\.summary/)
})

test("a cover shows as a thumbnail; otherwise the red tile", () => {
	assert.match(src, /<img\s+v-if="card\.cover_image"[^>]*class="g-ann-thumb"/)
	assert.match(src, /:tint="card\.cover_image \? '' : TILE\.announcement"/)
})

test("an urgent notice says so in words", () => {
	assert.match(src, /card\.urgent/)
	assert.match(src, /__\("Urgent"\)/)
})
