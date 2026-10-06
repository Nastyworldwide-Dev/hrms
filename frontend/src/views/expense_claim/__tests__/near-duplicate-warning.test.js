// Wiring of the near-duplicate warning (alpha.38): FormView announces a created document, the
// expense claim form asks the server about it and toasts what comes back. Source-asserted because
// the node runner does not compile SFCs (see Form.test.js); the behaviour itself is executed in
// utils/__tests__/nearDuplicateWarning.test.js.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const form = read("../Form.vue")
const formView = read("../../../components/FormView.vue")
const loud = read("../../../utils/loudRequest.js")

test("FormView announces the document it just created", () => {
	assert.match(formView, /defineEmits\(\[[^\]]*"created"/)
	const insert = formView.slice(formView.indexOf("insert: {"), formView.indexOf("setValue: {"))
	assert.match(insert, /emit\("created", data\)/)
	assert.ok(
		insert.indexOf('emit("created", data)') < insert.indexOf("router.replace"),
		"announced before the screen moves on"
	)
})

test("the expense claim form listens for it and asks the server for that claim", () => {
	assert.match(form, /@created="onCreated"/)
	assert.match(form, /url:\s*"hrms\.api\.near_duplicate_expenses"/)
	assert.match(form, /warnOfNearDuplicates\(/)
	assert.match(form, /notify:\s*gToast/)
})

test("a failed warning lookup is not toasted as 'Something didn't load' over a created claim", () => {
	const silent = loud.slice(loud.indexOf("const SILENT_ENDPOINTS"), loud.indexOf("])", loud.indexOf("const SILENT_ENDPOINTS")))
	assert.match(silent, /"hrms\.api\.near_duplicate_expenses"/)
})
