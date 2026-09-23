// A failed read is not an empty board. The list showed "Could not load
// announcements · Try again" AND "Nothing on the board — there is nothing live
// at the moment" at the same time: two opposite claims about one screen
// (audit P0-11). Same class Home's block fixed on 22 Sep (4fa619563).
// Source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../List.vue", import.meta.url)), "utf8")

test("the empty state only renders when the read did not fail", () => {
	const at = src.indexOf("__('Nothing on the board')")
	const tag = src.slice(src.lastIndexOf("<GEmptyState", at), at)
	assert.match(tag, /v-if="!rows\.length && !allAnnouncements\.error"/)
})
