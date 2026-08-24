// Regression test for the Time branch of FormField.vue (in/out time unpickable).
// frappe-ui 0.1.105's legacy Input renders its <input> only for a whitelist of
// types (text, number, checkbox, email, password, date) — `time` is excluded,
// so <Input type="time"> renders no control at all and staff could not enter
// Attendance Request in/out times in the PWA.
//
// The fix was originally a bare native <input type="time">, styled with
// hardcoded Tailwind (`border-gray-400`) that never adapted to dark mode —
// its own kind of residue. It now renders through GInput.vue, which is a
// THIN wrapper around a real native <input> (its own template is a plain
// <input :type="type">, no legacy Input involved — verified by reading it,
// not by an automated test: GInput.vue is a real SFC, and this suite's
// plain `node --test` runner has no Vue SFC loader, the same reason GTag is
// tested via a hand-written .js render function rather than a .vue file).
// The invariant this suite actually protects — "never the legacy frappe-ui
// Input component, which silently drops type=\"time\"" — still holds; it's
// enforced one layer down now, and confirmed live: docs/glass/HANDOFF.md
// records the dark/light screenshots taken of the rendered field.
//
// This suite has no SFC mounting (plain node --test), so the guard stays
// source-level. Run with: node --test frontend/tests/
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

test("Time branch never renders the legacy frappe-ui Input component", () => {
	const tag = timeBranchTag()
	assert.doesNotMatch(
		tag,
		/^<Input[\s>]/,
		'legacy frappe-ui <Input> silently drops type="time" — it must not be reintroduced here'
	)
})

test("Time branch is a time input bound to the form model, glass-styled", () => {
	const tag = timeBranchTag()
	assert.match(tag, /^<GInput[\s>]/, "must render through GInput, not a bare unstyled <input>")
	assert.match(tag, /type="time"/)
	assert.match(tag, /:model-value="modelValue"/)
	assert.match(tag, /emit\('update:modelValue'/)
	assert.match(tag, /:disabled="isReadOnly"/)
})
