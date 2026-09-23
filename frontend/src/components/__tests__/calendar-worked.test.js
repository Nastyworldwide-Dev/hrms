// "Worked" is ONE rule (owner bug, 23 Sep 2026). A day with an IN followed by
// an OUT is worked before auto-attendance writes its row, and today with an
// open IN is "in progress". The key names the Fix dot and In progress.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { dayState } from "../../utils/calendarDayState.js"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("attendance wins; a paired day with no row is worked; today's open IN is in progress", () => {
	const flags = { paired: ["2026-09-22"], open_today: "2026-09-23" }
	assert.equal(dayState("absent", "2026-09-22", flags), "absent")
	assert.equal(dayState("present", "2026-09-23", flags), "present")
	assert.equal(dayState("none", "2026-09-22", flags), "present")
	assert.equal(dayState("none", "2026-09-23", flags), "progress")
	assert.equal(dayState("none", "2026-09-21", flags), "none")
	assert.equal(dayState("none", "2026-09-22", undefined), "none")
})

test("the grid reads the flags' paired days and the key names Fix and In progress", () => {
	const cal = read("../AttendanceCalendar.vue")
	assert.match(cal, /dayState\(/)
	assert.match(cal, /state: "needs_you", label: __\("Fix"\)/)
	assert.match(cal, /state: "progress", label: __\("In progress"\)/)
	assert.match(cal, /\.g-cal__swatch--needs_you/)
	assert.match(cal, /\.g-cal__day--progress/)
	assert.match(cal, /\.g-cal__swatch--progress/)
})
