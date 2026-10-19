// Ticket #4855 family (design review of 2e617bb0a): a greyed-out Send with no
// visible reason reads as a frozen app. Two states still did it: an empty
// reason, and a cleared time. Each now says what is missing, at the button.
// Source-asserted (no SFC compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(
	fileURLToPath(new URL("../LateCheckoutDialog.vue", import.meta.url)),
	"utf8"
)
const template = src.slice(0, src.indexOf("<script"))

test("a cleared time says to pick one", () => {
	const fn = src.slice(src.indexOf("const checkoutError"))
	assert.match(fn, /if \(!checkoutTime\.value\) return __\("Pick the time you left\."\)/)
})

test("an empty reason says it is needed, beside Send", () => {
	assert.match(src, /const missingReason = computed\(\(\) => !reason\.value\.trim\(\)\)/)
	const at = template.indexOf("__('Send')")
	const after = template.slice(at)
	assert.match(after, /v-else-if="missingReason"[^>]*>\s*\{\{ __\("Add a reason to send\."\) \}\}/)
})
