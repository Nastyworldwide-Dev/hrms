// Back pressed right after tapping a day left the day sheet open over Home
// (reproduced on HEAD 3 of 5 runs, 23 Sep). The sheet noted the page it
// belongs to in willPresent, which runs after Ionic starts presenting; by
// then Back had already landed, so it noted Home and never closed. The page
// is noted when the sheet is ASKED to open (isOpen turns true), which is
// still on the page that asked.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GModal.vue", import.meta.url)), "utf8")

test("the page is noted when isOpen turns true", () => {
	assert.match(src, /watch\(\s*\(\) => props\.isOpen,\s*\(open\) => \{\s*if \(open\) openedOn = route\.path/)
})

test("willPresent keeps that note (trigger-opened sheets fall back to it)", () => {
	assert.match(src, /function onWillPresent\(\) \{\s*openedOn \?\?= route\.path/)
})

test("the note is cleared when the sheet closes", () => {
	assert.match(src, /function onDidDismiss\(\) \{[^}]*openedOn = null/)
})
