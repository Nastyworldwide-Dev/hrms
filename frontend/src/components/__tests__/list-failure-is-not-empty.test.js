// alpha.12 C2 (measured 26 Sep 2026, states-audit with every /api/ answer a
// 500): eleven list and profile screens said "No leave taken this year" /
// "No expense claims yet" — the page read as if the person's records were
// gone. The list only asked the server after the workflow lookup resolved;
// when that failed, onMounted threw before fetchDocumentList(), the list
// request never ran, `documents.error` stayed empty and the empty state won.
// Apple (loading): a blank or wrong screen "can make people think your app is
// frozen"; R7: never a loading or failed state shown as "nothing".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../ListView.vue", import.meta.url)), "utf8")
const mounted = src.slice(src.indexOf("onMounted(async () => {"))

test("the list asks the server even when the workflow lookup fails", () => {
	const wait = mounted.indexOf("workflowDoc.promise")
	assert.ok(wait > 0, "the workflow is still awaited for its state field")
	// the await is guarded, so a rejection cannot skip the fetch below it
	assert.match(mounted.slice(0, wait + 400), /try\s*\{[\s\S]*workflowDoc\.promise[\s\S]*\}\s*catch/)
	assert.ok(mounted.indexOf("fetchDocumentList()", wait) > wait)
})

test("the empty state is never drawn while a list request has failed or not run", () => {
	const tpl = src.slice(src.indexOf("<template>"), src.indexOf("<script"))
	const empty = tpl.slice(tpl.indexOf("<GEmptyState"), tpl.indexOf("</GEmptyState>") > 0 ? tpl.indexOf("</GEmptyState>") : tpl.indexOf("/>", tpl.indexOf("<GEmptyState")))
	assert.match(empty, /v-else-if="documents\.fetched"|v-else-if="listAnswered"/)
})

test("the failure names the list in plain words, never the doctype", () => {
	assert.doesNotMatch(src, /:what="props\.doctype\?\.toLowerCase\(\)"/)
	assert.match(src, /:what="listNoun"/)
})

// alpha.12 Q1: lists are in the order things were asked, newest first. By
// `modified` an old request jumped to the top whenever anyone touched it.
test("a list is newest-first by when it was sent, not when it was last touched", () => {
	assert.match(src, /default: "creation desc"/)
	assert.doesNotMatch(src, /default: "modified desc"/)
})
