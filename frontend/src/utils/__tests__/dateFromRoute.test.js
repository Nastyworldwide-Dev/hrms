// "Fix this day" and "Claim" from a Calendar day open their form with that day
// already chosen (approved Calendar plan, D2). The day sheet sent ?date= and
// neither form read it, so people re-picked the date. Only a real, well-formed
// date is accepted from the URL.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { dateFromRoute } from "../dateFromRoute.js"

test("a well-formed date is taken", () => {
	assert.equal(dateFromRoute({ date: "2026-09-10" }), "2026-09-10")
})

test("anything else is ignored", () => {
	for (const bad of [
		undefined,
		"",
		"10/09/2026",
		"2026-9-10",
		"2026-02-31",
		["2026-09-10"],
		"2026-09-10T00:00",
	]) {
		assert.equal(dateFromRoute({ date: bad }), null, String(bad))
	}
})

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("both forms read the day from the route", () => {
	assert.match(
		read("../../views/attendance/AttendanceRequestForm.vue"),
		/dateFromRoute\(route\.query\)/
	)
	assert.match(read("../../views/ot/OTRequestForm.vue"), /dateFromRoute\(route\.query\)/)
})
