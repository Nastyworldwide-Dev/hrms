// alpha.14 (owner, 27 Sep 2026: "the calendar should be read only. as it
// state for my request. not changing." — ruled "go on edit"). A request once
// sent is not edited in the app, even while it waits: the owner's waiting
// overtime request let him change its date, hours and note. Frappe allows it
// (a Waiting request is an unsubmitted draft), so the rule is the app's: to
// change one, withdraw it and send a new one. The approver decides through
// the review sheet, never by editing fields, so nothing is taken from them.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const form = read("../FormView.vue")
const sheet = read("../RequestActionSheet.vue")

test("a sent request's form is read-only, whatever its status", () => {
	const body = form.slice(form.indexOf("const isFormReadOnly = computed"), form.indexOf("onMounted(async"))
	assert.match(body, /return Boolean\(props\.id\)/)
})

test("the request sheet offers Withdraw, not Edit", () => {
	assert.doesNotMatch(sheet, /:label="__\('Edit'\)"/)
	assert.match(sheet, /:label="__\('Withdraw'\)"/)
})

test("a sent request never offers Save", () => {
	const button = form.slice(form.indexOf("const formButton = computed"), form.indexOf("const cancelAsRow"))
	assert.match(button, /!props\.id && formModel\.value\.docstatus !== 2/)
	assert.match(form, /\(isFormDirty && !isFormReadOnly\)/)
})
