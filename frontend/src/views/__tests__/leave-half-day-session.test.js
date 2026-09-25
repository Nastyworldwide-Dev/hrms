// Half day AM/PM (owner, 25 Sep 2026: "the missing feature is am/pm for
// halfday … make sure these whole stuff is clear with guidance"). The form
// asks which half, only for a half day, and each choice says what it means in
// the person's own shift ("AM — Off in the morning. Start by 13:30.").
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { sessionGuidance, sessionOptions } from "../../utils/halfDaySession.js"

const form = readFileSync(fileURLToPath(new URL("../leave/Form.vue", import.meta.url)), "utf8")

test("the half-day session is asked, and only for a half day", () => {
	assert.match(form, /"half_day_session",/, "on the form's field list")
	assert.match(form, /session\.hidden = !half_day/)
	assert.match(form, /session\.reqd = Boolean\(half_day\)/)
})

test("a picked half fits the row: short, with its clock", () => {
	const hints = { AM_short: "start 13:30", PM_short: "leave 13:30" }
	assert.deepEqual(sessionOptions(hints, (s) => s), [
		{ value: "AM", label: "AM · start 13:30" },
		{ value: "PM", label: "PM · leave 13:30" },
	])
	assert.deepEqual(sessionOptions(null, (s) => s), [
		{ value: "AM", label: "AM" },
		{ value: "PM", label: "PM" },
	])
})

test("the line under the choice says what it means, in full", () => {
	const hints = { AM: "Off in the morning. Start by 13:30.", PM: "Off in the afternoon. Leave at 13:30." }
	assert.equal(sessionGuidance(hints, "AM", (s) => s), "Off in the morning. Start by 13:30.")
	assert.equal(sessionGuidance(hints, "PM", (s) => s), "Off in the afternoon. Leave at 13:30.")
	assert.equal(sessionGuidance(null, "", (s) => s), "AM if you are off in the morning, PM if you leave at mid-shift.")
	assert.match(form, /v-if="leaveApplication\.half_day && groupHasSession\(group\)"\s*class="g-form-footer g-halfday-note"\s*role="status"/)
})

test("the guidance is read for the half-day date, from the caller's shift", () => {
	assert.match(form, /url: "hrms\.api\.half_day\.get_half_day_hints"/)
	assert.match(form, /day: leaveApplication\.value\.half_day_date/)
})
