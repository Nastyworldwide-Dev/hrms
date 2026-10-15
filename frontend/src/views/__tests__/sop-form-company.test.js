// An SOP posted from Nadi for everyone reached one company only (owner, 15 Oct 2026).
// The form sent no company; Frappe filled in the HR user's own company from their
// Company permission (update_if_missing fills a MISSING value, not an empty one).
// The form now has a Companies picker, "All companies" by default, and always sends it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const form = readFileSync(fileURLToPath(new URL("../sop/SopFormSheet.vue", import.meta.url)), "utf8")

test("a save sends the company, empty meaning all companies", () => {
	assert.match(form, /values\.company = sopCompany\.value \|\| ""/)
})

// Security review of e6e42d136: an edit saved before the SOP's company was read
// sent "" and silently widened it to every company.
test("an edit sends the company only once it has been read", () => {
	assert.match(form, /if \(companyReady\.value\) values\.company/)
	assert.match(form, /companyReady\.value = !props\.sopName/)
	assert.match(form, /:disabled="!companyReady"/)
})

test("the picker offers All companies first, and the site's companies", () => {
	assert.match(form, /\{ value: "", label: __\("All companies"\) \}/)
	assert.match(form, /url: "hrms\.api\.get_company_currencies"/)
	assert.match(form, /:model-value="sopCompany"/)
})

// Design review of e6e42d136.
test("the saved company is always a choice, and the label is singular", () => {
	assert.match(form, /if \(sopCompany\.value\) names\.add\(sopCompany\.value\)/)
	assert.match(form, /__\("Company"\)/)
	assert.doesNotMatch(form, /__\("Companies"\)/)
})

test("a department SOP's line names its company too", () => {
	assert.match(form, /__\("\{0\}, in \{1\}", \[dept, sopCompany\.value\]\)/)
})
