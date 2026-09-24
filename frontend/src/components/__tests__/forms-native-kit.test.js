// The form kit is Glass all the way down. The owner's "New Leave Application"
// screenshot still showed frappe-ui's grey boxes ("Select Leave Type",
// "Select From Date") because FormField, Link and the date wrappers rendered
// frappe-ui's Autocomplete / DatePicker / DateTimePicker / Input / ErrorMessage
// under a Glass coat. Native inputs with the Glass skin replace them; only the
// rich TextEditor stays frappe-ui (nothing native does rich text).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")

const files = {
	"FormField.vue": "../FormField.vue",
	"Link.vue": "../Link.vue",
	"GDatePicker.vue": "../glass/GDatePicker.vue",
	"GDateTimePicker.vue": "../glass/GDateTimePicker.vue",
}

// frappe-ui names that are not the grey field kit: TextEditor (rich text has
// no native control) and Link.vue's data plumbing (createResource, debounce)
const ALLOWED = new Set(["TextEditor", "createResource", "debounce"])

for (const [name, rel] of Object.entries(files)) {
	test(`${name} renders no frappe-ui field widget (TextEditor excepted)`, () => {
		const src = read(rel)
		const imported = [...src.matchAll(/import\s*\{([^}]*)\}\s*from\s*"frappe-ui"/g)]
			.flatMap((m) => m[1].split(","))
			.map((s) => s.trim())
			.filter(Boolean)
		const widgets = imported.filter((n) => !ALLOWED.has(n))
		assert.deepEqual(widgets, [], `${name} still imports ${widgets.join(", ")} from frappe-ui`)
		assert.doesNotMatch(src, /import\s+\w+\s+from\s*"frappe-ui/, "no default/deep frappe-ui import")
	})
}

test("FormField carries no raw gray utility classes", () => {
	assert.doesNotMatch(read("../FormField.vue"), /\b(border|bg|text)-gray-\d+/)
})

test('FormField placeholders never say "Select X"', () => {
	assert.doesNotMatch(read("../FormField.vue"), /["']Select \{0\}["']/)
})

test("FormField routes each fieldtype to its Glass control", () => {
	const src = read("../FormField.vue")
	// Check is a switch in its row (alpha.6 B3, HIG Toggles), not a checkbox.
	for (const tag of ["GSelect", "GDatePicker", "GDateTimePicker", "GSwitch"]) {
		assert.match(src, new RegExp(`<${tag}[\\s>]`), `FormField must render <${tag}>`)
	}
	assert.match(src, /<p[^>]*class="g-field-error"/, "error is a plain Glass line")
	assert.match(src, /sentenceCase\(/, "labels go through sentenceCase")
})
