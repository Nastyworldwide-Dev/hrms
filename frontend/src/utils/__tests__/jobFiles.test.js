// Optional files with the draft job description (owner, 29 Oct 2026).
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

import { withFile, withoutFile } from "../jobFiles.js"

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
