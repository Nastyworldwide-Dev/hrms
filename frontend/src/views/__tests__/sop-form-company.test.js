// An SOP posted from Nadi for everyone reached one company only (owner, 15 Oct 2026).
// The form sent no company; Frappe filled in the HR user's own company from their
// Company permission (update_if_missing fills a MISSING value, not an empty one).
// The form now has a Companies picker, "All companies" by default, and always sends it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const form = readFileSync(fileURLToPath(new URL("../sop/SopFormSheet.vue", import.meta.url)), "utf8")

test("every save sends the company, empty meaning all companies", () => {
	assert.match(form, /company: sopCompany\.value \|\| "",/)
})

test("the picker offers All companies first, and the site's companies", () => {
	assert.match(form, /\{ value: "", label: __\("All companies"\) \}/)
	assert.match(form, /url: "hrms\.api\.get_company_currencies"/)
	assert.match(form, /:model-value="sopCompany"/)
})
