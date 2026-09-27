// alpha.14 (owner, 27 Sep 2026: "every attachment must show preview"). Three
// places listed a file as its name only: a request's form, the request
// sheet, and a new ticket. One row now: an image shows itself, a PDF and
// other files a typed mark; a tap opens the full preview.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { attachmentKind } from "../attachmentKind.js"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("an image by its name or url, including what phones save", () => {
	for (const f of ["IMG_2231.JPG", "a.jpeg", "b.png", "c.webp", "d.heic", "e.gif"]) assert.equal(attachmentKind({ file_name: f }), "image", f)
	assert.equal(attachmentKind({ file_url: "/private/files/receipt.png?fid=1" }), "image")
})

test("a picked file not yet uploaded is read by its type", () => {
	assert.equal(attachmentKind({ name: "x", type: "image/jpeg" }), "image")
	assert.equal(attachmentKind({ name: "x", type: "application/pdf" }), "pdf")
})

test("pdf and the rest", () => {
	assert.equal(attachmentKind({ file_name: "medical-cert.PDF" }), "pdf")
	assert.equal(attachmentKind({ file_name: "sheet.xlsx" }), "file")
	assert.equal(attachmentKind({}), "file")
})

test("every list of attachments uses the one previewing row", () => {
	for (const file of ["../../components/FileUploaderView.vue", "../../components/RequestActionSheet.vue", "../../components/glass/GFileUpload.vue"]) {
		const src = read(file)
		assert.match(src, /<GAttachmentRow\b/, file)
		assert.doesNotMatch(src, /\{\{\s*file\.file_name \|\| file\.name\s*\}\}/, file)
	}
})

// Found while wiring the rows (27 Sep 2026): the IT ticket form bound
// <GFileUpload v-model="files"> but GFileUpload never emits update:modelValue
// — it emits select / preview / remove. A screenshot picked there went
// nowhere and was never uploaded. The form now handles all three.
test("the ticket form keeps what is picked, previews it, and can remove it", () => {
	const src = read("../../views/helpdesk/TicketNew.vue")
	const tag = src.match(/<GFileUpload\b[^>]*\/>/)[0]
	assert.match(tag, /@select="addFiles"/)
	assert.match(tag, /@preview="previewFile"/)
	assert.match(tag, /@remove="removeFile"/)
	assert.match(src, /<FilePreviewModal\b/)
})
