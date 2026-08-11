// Regression test for the Time branch of FormField.vue (in/out time unpickable).
// frappe-ui 0.1.105's legacy Input renders its <input> only for a whitelist of
// types (text, number, checkbox, email, password, date) — `time` is excluded,
// so <Input type="time"> renders no control at all and staff could not enter
// Attendance Request in/out times in the PWA. The fix renders a native
// <input type="time"> instead. This suite has no SFC mounting (plain node
// --test), so the guard is source-level: the Time branch must be a native
// input, never the legacy Input component. Run with: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	join(dirname(fileURLToPath(import.meta.url)), "../src/components/FormField.vue"),
	"utf8"
)

// grab the element whose v-else-if guards the Time fieldtype
function timeBranchTag() {
	const cond = source.indexOf("props.fieldtype === 'Time'")
	assert.notEqual(cond, -1, "FormField.vue must have a Time fieldtype branch")
	const start = source.lastIndexOf("<", cond)
	const end = source.indexOf("/>", cond)
	assert.notEqual(end, -1, "Time branch tag must be self-closing")
	return source.slice(start, end + 2)
}

test("Time branch renders a native input, not the legacy frappe-ui Input", () => {
	const tag = timeBranchTag()
	assert.match(
		tag,
		/^<input[\s>]/,
		"legacy frappe-ui <Input> silently drops type=\"time\" — use a native <input>"
	)
})

test("Time branch is a time input bound to the form model", () => {
	const tag = timeBranchTag()
	assert.match(tag, /type="time"/)
	assert.match(tag, /:value="modelValue"/)
	assert.match(tag, /emit\('update:modelValue'/)
	assert.match(tag, /:disabled="isReadOnly"/)
})
