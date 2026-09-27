// alpha.14 G (27 Sep 2026 sweep): a sent-and-decided request (Time off
// Rejected, Expense Approved) still offered "Add a file" and a remove X on
// its files. Frappe refuses to change a submitted document's attachments
// through the app, and nothing about a decided request changes with a new
// file. Its files are shown, read-only; the picker is for a request still
// being written.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the form passes read-only to its files", () => {
	const form = read("../FormView.vue")
	const uses = form.match(/<FileUploaderView\b[^>]*\/>/g)
	assert.equal(uses.length, 2)
	for (const tag of uses) assert.match(tag, /:readOnly="isFormReadOnly"/)
})

test("read-only files: no Add a file, no remove", () => {
	const view = read("../FileUploaderView.vue")
	assert.match(view, /<label v-if="!readOnly" class="file-select">/)
	assert.match(view, /:removable="!readOnly"/)
	assert.match(view, /readOnly: \{ type: Boolean, default: false \}/)
})

test("a decided request with no files shows no file area at all", () => {
	const view = read("../FileUploaderView.vue")
	assert.match(view, /<div v-if="!readOnly \|\| modelValue\.length" class="flex flex-col gap-3 py-4">/)
})
