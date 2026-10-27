// alpha.7 §10.1/§10.2: a Home card is the title, HR's Summary (not text cut
// from the body), and the cover as a small thumbnail when there is one;
// the red announcement tile otherwise. Must-read waits with a word.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Announcements.vue", import.meta.url)), "utf8")
// The badge and the line under the title moved to one shared rule (27 Oct 2026) so the board
// and Home cannot drift apart; the same assertions now read it where the code lives.
const rule = readFileSync(
	fileURLToPath(new URL("../../utils/announcementRow.js", import.meta.url)),
	"utf8"
)

test("Home reads the shared row rule rather than keeping its own", () => {
	assert.match(src, /from "@\/utils\/announcementRow"/)
})

test("the preview line is HR's summary", () => {
	assert.match(rule, /card\.summary/)
})

test("a cover shows as a thumbnail; otherwise the red tile", () => {
	assert.match(src, /<img\s+v-if="card\.cover_image"[^>]*class="g-ann-thumb"/)
	assert.match(src, /:tint="card\.cover_image \? '' : TILE\.announcement"/)
})

test("an urgent notice says so in words", () => {
	assert.match(rule, /card\.urgent/)
	assert.match(rule, /__\("Urgent"\)/)
})
