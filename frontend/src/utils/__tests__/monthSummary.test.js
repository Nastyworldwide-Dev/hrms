// alpha.13 slice 2: one line above the Calendar grid — "18 days worked · 2 to
// fix" — counted from the SAME days the grid draws, so the line and the tiles
// can never disagree.
import { test } from "node:test"
import assert from "node:assert/strict"
import { monthSummary } from "../monthSummary.js"

const day = (state, flags = []) => ({ state, flags })

test("worked days and days to fix, from the drawn tiles", () => {
	const days = [day("present"), day("present", ["needs_you"]), day("half"), day("absent"), day("none", ["needs_you"]), day("rest"), day("progress")]
	assert.deepEqual(monthSummary(days), { worked: 3, toFix: 2 })
})

test("an empty month says nothing, not zeroes", () => {
	assert.equal(monthSummary([day("none"), day("rest")]), null)
})

test("half days count as worked; today in progress does not yet", () => {
	assert.deepEqual(monthSummary([day("half"), day("progress")]), { worked: 1, toFix: 0 })
})

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
const cal = readFileSync(fileURLToPath(new URL("../../components/AttendanceCalendar.vue", import.meta.url)), "utf8")

test("the line sits under the grid as its footer, and 'to fix' opens the first such day", () => {
	assert.match(cal, /monthSummary\(days\.value\)/)
	assert.match(cal, /class="g-form-footer g-cal__summary"/)
	assert.match(cal, /@click="openFirstToFix"/)
})
