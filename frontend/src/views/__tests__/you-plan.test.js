// The You page (audit-pages §4 "You"; owner ruling 3: show the shift pattern).
// Who I am and how the app behaves for me, on ONE page:
// - title "You"; department · branch under the name
// - "Your manager is …" and "Your shift: …" on the page, not in sheets
// - ONE "Your details" row, one sheet (was three rows, three sheets)
// - theme and notifications inline; the Settings page is cut
// - version as a plain line, not a button; "Log out"
// - no group eyebrows
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const at = (path) => fileURLToPath(new URL(path, import.meta.url))
const view = readFileSync(at("../Profile.vue"), "utf8")
const template = view.slice(0, view.indexOf("<script"))

test("the page is called You", () => {
	assert.match(template, /__\(["']You["']\)/)
	assert.doesNotMatch(template, /__\("Profile"\)/)
})

test("manager and shift are on the page", () => {
	// alpha.8: label/value rows in the account group (you-account-card.test.js)
	assert.match(template, /__\(["']Manager["']\)/)
	assert.match(template, /__\(["']Shift["']\)/)
	assert.match(view, /default_shift/)
})

test("one details row, one sheet", () => {
	assert.match(view, /__\("Your details"\)/)
	assert.doesNotMatch(view, /__\("Company information"\)|__\("Contact information"\)/)
	assert.doesNotMatch(view, /ContactInfoSheet/)
})

test("theme and notifications are on the page; Settings is gone", () => {
	// alpha.6 B3: Appearance is a menu row (HIG Pickers), not a segmented bar.
	assert.match(template, /<GSelect[\s\S]*?THEME_OPTIONS/)
	assert.match(template, /__\(['"]Notifications['"]\)/)
	assert.doesNotMatch(view, /name: "Settings"/)
	assert.ok(!existsSync(at("../AppSettings.vue")), "the Settings page is deleted")
})

test("the version is a line, not a button", () => {
	assert.match(template, /__\("Version \{0\} · \{1\}"/)
	assert.doesNotMatch(view, /About this app/)
})

test("no group eyebrows", () => {
	assert.doesNotMatch(template, /g-eyebrow/)
})

test("nothing the old sheets showed was lost (review of 518a541e7)", () => {
	for (const field of ["grade", "prefered_email", "company_email", "department"]) {
		assert.match(view, new RegExp(`"${field}"`), `${field} is still in Your details`)
	}
})

test("turning notifications off says so, as Settings did", () => {
	assert.match(view, /__\("Notifications are off"\)/)
})
