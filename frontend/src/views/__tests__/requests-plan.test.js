// The Requests page plan (audit-flows §4A, AUDIT-PLAN P1-B): one "New request"
// button opening a type sheet replaces the six-tile grid that pushed the list
// below the fold (P and M4 both; L-HICK, S-TILE). Asking HR is not a request:
// it lives on Help. Fixing a day starts from the day, on Calendar.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Requests.vue", import.meta.url)), "utf8")
const template = src.slice(0, src.indexOf("<script"))

test("one New request button, no tile grid", () => {
	assert.doesNotMatch(template, /<QuickLinks/)
	assert.match(template, /:label="__\('New request'\)"/)
	assert.match(template, /<GActionSheet/)
})

test("the type sheet lists the request types, and nothing that is not a request", () => {
	for (const type of ["Time off", "Claim overtime", "Claim an expense", "Change a shift", "Fix a day"]) {
		assert.match(src, new RegExp(`__\\("${type}"\\)`), type)
	}
	assert.doesNotMatch(src, /HR Issues|Issue board/)
})

test("Fix a day opens the fix form, so the person stays in Requests", () => {
	// It pushed the Calendar into the Requests tab (a5 item 6); the form asks
	// for the date itself.
	assert.match(src, /fix: \{ name: "AttendanceRequestFormView" \}/)
	assert.doesNotMatch(src, /fix: \{ name: "AttendanceDashboard" \}/)
})
