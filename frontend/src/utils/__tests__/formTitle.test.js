// A form's title is the person's word for the request, never the doctype
// (ruling L4: doctype names and IDs never reach users).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { formTitle } from "../formTitle.js"

test("a new request is titled by its kind", () => {
	assert.equal(formTitle("Leave Application", true), "Time off")
	assert.equal(formTitle("OT Request", true), "Overtime")
	assert.equal(formTitle("Expense Claim", true), "Expense")
	assert.equal(formTitle("Shift Request", true), "Shift change")
	assert.equal(formTitle("Attendance Request", true), "Fix a day")
})

test("an existing request is titled by its kind too", () => {
	assert.equal(formTitle("Leave Application", false), "Time off")
})

test("an issue is an Issue; an unknown doctype is a Request, never its name", () => {
	assert.equal(formTitle("Employee Issue", true), "Issue")
	assert.equal(formTitle("Some Internal Doctype", false), "Request")
})

const form = readFileSync(fileURLToPath(new URL("../../components/FormView.vue", import.meta.url)), "utf8")
const template = form.slice(0, form.indexOf("<script"))

test("the form shell shows no doctype name as a title", () => {
	assert.doesNotMatch(template, /:title="[^"]*__\(props\.doctype\)/)
	assert.doesNotMatch(template, /New \{0\}/)
	assert.match(template, /formTitle\(props\.doctype, !id\)/)
})

test("confirms never show the record id", () => {
	assert.doesNotMatch(template, /\{\{\s*formModel\.name\s*\}\}/)
})
