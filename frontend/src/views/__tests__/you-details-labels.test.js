// "Your details" showed five rows with no label (live audit 23 Sep):
// department, designation, branch, grade, employment type. Their labels came
// from get_doctype_fields, which by design leaves out links the employee
// cannot open (the fields a form can fill in). A read-only sheet must not
// depend on that list: every row has its own plain label, and an empty value
// is left out rather than shown as "-".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const view = readFileSync(fileURLToPath(new URL("../Profile.vue", import.meta.url)), "utf8")

test("every detail row carries its own label", () => {
	const block = view.slice(
		view.indexOf("const DETAILS = ["),
		view.indexOf("]\n", view.indexOf("const DETAILS = ["))
	)
	for (const [field, label] of [
		["department", "Department"],
		["designation", "Job title"],
		["branch", "Branch"],
		["grade", "Grade"],
		["employment_type", "Employment type"],
	]) {
		assert.match(block, new RegExp(`\\["${field}", __\\("${label}"\\)`), `${field} → ${label}`)
	}
})

test("labels no longer come from the fillable-fields list", () => {
	assert.doesNotMatch(view, /get_doctype_fields/)
})

test("empty values are left out, not shown as a dash", () => {
	assert.match(
		view,
		/\.filter\(\(row\) => row\.value !== null && row\.value !== undefined && row\.value !== ""\)/
	)
})

// The Employee field is spelt "prefered_email" (ERPNext's own spelling, the
// one every server reader in hrms uses). "preferred_email" reads undefined,
// and the empty-row filter above then hides the row without a trace.
test("the preferred email row reads the field Employee really has", () => {
	assert.match(view, /\["prefered_email", __\("Preferred email"\)/)
	assert.doesNotMatch(view, /"preferred_email"/)
})
