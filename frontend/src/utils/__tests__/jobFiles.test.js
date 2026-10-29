// Optional files with the draft job description (owner, 29 Oct 2026).
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

import { JOB_FILE_TYPES, shouldFillFrom, withFile, withoutFile } from "../jobFiles.js"

const A = { file_url: "/private/files/jd.pdf", file_name: "jd.pdf" }
const B = { file_url: "/private/files/org.png", file_name: "org.png" }

test("files are added in the order picked, any number", () => {
	assert.deepEqual(withFile(withFile([], A), B), [A, B])
})

test("the same file twice is one file", () => {
	assert.deepEqual(withFile([A], { ...A }), [A])
})

test("a failed upload with no URL adds nothing", () => {
	assert.deepEqual(withFile([A], {}), [A])
	assert.deepEqual(withFile([A], null), [A])
})

test("a file can be taken off before sending, leaving the others", () => {
	assert.deepEqual(withoutFile([A, B], A), [B])
	assert.deepEqual(withoutFile([], A), [])
})

test("the wizard draws the row right after the draft job description, and it is never required", () => {
	const src = readFileSync(
		new URL("../../views/manpower/ManpowerRequestWizard.vue", import.meta.url),
		"utf8"
	)
	assert.match(src, /<JobFilesRow[\s\S]{0,200}v-if="isJobDescription\(q\)"/)
	assert.match(src, /v-model:files="model\.job_files"/)
	const row = readFileSync(new URL("../../components/JobFilesRow.vue", import.meta.url), "utf8")
	assert.match(row, /Attachments \(optional\)/)
	// never a required field: no reqd attribute or "Required" label in its template
	const template = row.slice(row.indexOf("<template>"), row.indexOf("</template>"))
	assert.doesNotMatch(template, /reqd|__\("Required"\)/)
})

test("a file still uploading holds Next and Send", () => {
	const src = readFileSync(
		new URL("../../views/manpower/ManpowerRequestWizard.vue", import.meta.url),
		"utf8"
	)
	const blocker = src.slice(
		src.indexOf("const blocker = computed"),
		src.indexOf("const groups = computed")
	)
	assert.match(blocker, /if \(filesUploading\.value\) return/)
})

test("the request page lists its files, read through the request's own check", () => {
	const src = readFileSync(
		new URL("../../views/manpower/ManpowerRequestDetail.vue", import.meta.url),
		"utf8"
	)
	assert.match(src, /url: "hrms\.api\.get_attachments"/)
	assert.match(src, /<section v-if="jobFiles\.length"/)
})

// The JD file fills the Draft job description box (owner, 29 Oct 2026): "it will auto
// reflect the job description but still can be edit".
test("an attached JD fills the box only while the box is empty and the file can hold text", () => {
	assert.equal(shouldFillFrom("", { file_name: "JD Marketing.pdf" }), true)
	assert.equal(shouldFillFrom("  \n", { file_name: "jd.DOCX" }), true)
	assert.equal(shouldFillFrom(undefined, { file_name: "jd.txt" }), true)
	// never over what the person typed or an earlier file filled
	assert.equal(shouldFillFrom("Sell things", { file_name: "jd.pdf" }), false)
	// a photo or an old .doc has no text to take
	for (const name of ["org.png", "jd.jpg", "jd.doc", "jd"])
		assert.equal(shouldFillFrom("", { file_name: name }), false, name)
	assert.equal(shouldFillFrom("", null), false)
})

test("the picker takes Word and text files as well as PDF and photos", () => {
	for (const type of [".pdf", ".docx", ".doc", ".txt", "image/jpeg", "image/png"])
		assert.ok(JOB_FILE_TYPES.split(",").includes(type), type)
})

test("the wizard fills the box from an upload, through the reader, and the box stays editable", () => {
	const src = readFileSync(
		new URL("../../views/manpower/ManpowerRequestWizard.vue", import.meta.url),
		"utf8"
	)
	assert.match(src, /@uploaded="fillFromFile\(q, \$event\)"/)
	assert.match(src, /hrms\.utils\.job_description_text\.read_job_description/)
	assert.match(src, /shouldFillFrom\(extra\[key\], file\)/)
	const row = readFileSync(new URL("../../components/JobFilesRow.vue", import.meta.url), "utf8")
	assert.match(row, /emit\("uploaded", uploaded\)/)
	assert.match(row, /:accept="JOB_FILE_TYPES"/)
})

test("reading a JD holds Next and Send on its own flag, so the upload finishing cannot release it", () => {
	const src = readFileSync(
		new URL("../../views/manpower/ManpowerRequestWizard.vue", import.meta.url),
		"utf8"
	)
	const fill = src.slice(
		src.indexOf("async function fillFromFile"),
		src.indexOf("const leaveOpen")
	)
	assert.doesNotMatch(fill, /filesUploading/)
	assert.match(fill, /readingFiles\.value\+\+/)
	assert.match(fill, /readingFiles\.value--/)
	const blocker = src.slice(
		src.indexOf("const blocker = computed"),
		src.indexOf("const groups = computed")
	)
	assert.match(blocker, /readingFiles\.value/)
	// a failed read says so instead of only logging
	assert.match(fill, /catch \(error\) \{[\s\S]*gToast/)
})
