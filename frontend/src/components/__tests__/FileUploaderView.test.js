// A required attachment is shown as "Required" on the file row before Send,
// not only refused when Send is tapped (owner mockup, 14 Oct 2026: the
// expense claim's receipt). Source-asserted because the node runner does not
// compile SFCs (see FormView.test.js).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (f) => readFileSync(fileURLToPath(new URL(`../${f}`, import.meta.url)), "utf8")
const uploader = read("FileUploaderView.vue")
const form = read("FormView.vue")

test("the file row says Required while a required attachment is missing", () => {
	assert.match(uploader, /required: \{ type: Boolean, default: false \}/)
	assert.match(uploader, /v-if="required && !modelValue\.length"[^>]*>\{\{ __\("Required"\) \}\}/)
})

test("FormView passes requireAttachment to both file rows", () => {
	assert.equal((form.match(/:required="requireAttachment"/g) || []).length, 2)
})

test("a draft submitted later is refused without its required file too", () => {
	const update = form.slice(form.indexOf("async function handleDocUpdate"), form.indexOf("async function handleDocUpdate") + 900)
	assert.match(update, /action === "submit" && props\.requireAttachment && !fileAttachments\.value\.length/)
})
