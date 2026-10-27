// 27 Oct 2026 (intelligence gaps, item 2): a week with approved leave read
// "3 days worked" and nothing else, as if the other days were missed. The
// server now sends days_on_leave (whole days off, as the calendar reads them)
// and the line says both: "3 days worked · 2 on leave".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../HomeWeek.vue", import.meta.url)), "utf8")

test("the week line names days on leave beside days worked", () => {
	assert.match(src, /homeWeek\.data\?\.days_on_leave/)
	assert.match(src, /__\("\{0\} · 1 day on leave", \[worked\]\)/)
	assert.match(src, /__\("\{0\} · \{1\} days on leave", \[worked, leave\.value\]\)/)
})

test("a week with no leave reads as before", () => {
	assert.match(src, /if \(!leave\.value\) return worked/)
})
