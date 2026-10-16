// Owner report, 16 Oct 2026 ("Dia taknak bukak"): after Approve on /approvals the
// sheet stayed as an empty frame with only its X, and the next request would not
// open. RequestActionSheet closed itself with modalController.dismiss(), which
// closes WHICHEVER overlay is on top (its own confirm, a preview, or nothing while
// animating). When it missed, the host kept `selected` set, so is-open never went
// false then true again; and a failed reload of the request (doc -> null) left the
// body empty. The sheet now asks its host to close it, and always draws something.
// Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const sheet = read("../RequestActionSheet.vue")
const template = sheet.slice(0, sheet.indexOf("<script"))

test("the request sheet never closes whichever overlay is on top", () => {
	assert.doesNotMatch(sheet, /modalController/)
	assert.match(sheet, /defineEmits\(\[\s*"close"\s*\]\)/)
})

test("the delayed close after a decision is cancelled when the sheet goes away", () => {
	assert.match(sheet, /closeTimer = setTimeout\(\(\) => emit\("close"\), DECIDED_MS\)/)
	assert.match(sheet, /onBeforeUnmount\(\(\) => clearTimeout\(closeTimer\)\)/)
})

test("every host closes its own sheet when asked", () => {
	for (const [file, close] of [
		["../../views/Approvals.vue", /<RequestActionSheet[^>]*@close="selectedOpen = false"/],
		["../FormView.vue", /<RequestActionSheet[^>]*@close="showReviewSheet = false"/],
		["../RequestList.vue", /<RequestActionSheet[^>]*@close="isRequestModalOpen = false"/],
	])
		assert.match(read(file).replace(/\s+/g, " "), close, file)
})

test("the body is never an empty frame: loading and failed states draw", () => {
	assert.match(template, /v-if="document\?\.doc"/)
	assert.match(template, /v-else-if="document\.get\?\.error"/)
	assert.match(template, /<ResourceError :resource="document\.get"/)
	assert.match(template, /<GSkeleton/)
})

test("each request opens a fresh sheet, never the last one's document or mark", () => {
	for (const file of ["../../views/Approvals.vue", "../RequestList.vue"])
		assert.match(
			read(file).replace(/\s+/g, " "),
			/<RequestActionSheet[^>]*:key="`\$\{[^}]+\.doctype\}:\$\{[^}]+\.name\}`"/,
			file
		)
})

// Review of d3be5595d: clearing the request on close emptied the sheet for the
// length of its slide-out. Close lowers the open flag; the request is cleared
// on did-dismiss, after the sheet has gone.
test("a closing sheet keeps its content until it has slid out", () => {
	const approvals = read("../../views/Approvals.vue")
	assert.match(approvals, /<GModal :is-open="!!selected && selectedOpen" @did-dismiss="close">/)
	assert.match(approvals, /function close\(\) \{\s*selected\.value = null/)
	const form = read("../FormView.vue")
	assert.match(form, /function closeReviewSheet\(\) \{[\s\S]*?reviewRequest\.value = null/)
	const list = read("../RequestList.vue")
	assert.match(
		list,
		/const closeRequestModal = async \(\) => \{\s*isRequestModalOpen\.value = false\s*selectedRequest\.value = null/
	)
})
