// FormView renders its entire UI — header, Back button and all — inside
// `v-if="isFormReady"`. A slow or failed document fetch (404, no permission,
// dropped network) leaves isFormReady false forever, so without a v-else the
// screen is blank with no spinner, no error and no way back — on every one of
// the six request detail/edit views. This pins the recovery branch so it
// cannot silently regress. Source-asserted because the node runner does not
// compile SFCs (see router/__tests__).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../FormView.vue", import.meta.url)), "utf8")

test("a failed/slow document load has a recovery branch, not a blank screen", () => {
	// the happy UI is gated on isFormReady...
	assert.match(src, /v-if="isFormReady"/, "form UI is gated on isFormReady")
	// ...so there MUST be a sibling v-else that renders something.
	assert.match(
		src,
		/<div v-else class="flex flex-col h-full w-full form-view-root">/,
		"must have a v-else recovery branch"
	)
})

test("the recovery branch gives the user a way out (Back + Try again)", () => {
	// find the v-else block and assert it carries an escape hatch.
	const elseIdx = src.indexOf("<div v-else")
	assert.ok(elseIdx > 0, "v-else branch exists")
	const tail = src.slice(elseIdx)
	assert.match(tail, /goBackOrHome\(router\)/, "recovery branch must keep a Back action")
	assert.match(tail, /reloadDoc\(\)/, "recovery branch must offer Try again / retry")
	assert.match(
		tail,
		/documentResource\.get\.loading/,
		"recovery branch distinguishes loading from error"
	)
})

test("a refused creation shows the server's reason, not a generic 'Error creating'", () => {
	// "unknown error" report (15 Sep 2026): an employee's leave application was
	// refused and the toast said only "Error creating Leave Application". The
	// server names the reason (balance, allocation period, approver, holiday
	// list); the insert handler must carry it to the toast.
	const insertIdx = src.indexOf("insert: {")
	assert.ok(insertIdx > 0, "docList.insert handler exists")
	const insertBlock = src.slice(insertIdx, src.indexOf("setValue: {", insertIdx))
	assert.match(insertBlock, /onError\(error\)/, "the insert error handler receives the error")
	assert.match(
		insertBlock,
		/firstMessage\(error\)/,
		"the toast text carries the server's first message"
	)
})

test("the form's error is the Glass error line: said aloud, plain text, same place", () => {
	// The last frappe-ui control in FormView was <ErrorMessage>: v-html on a raw
	// server string, in frappe-ui's red, outside the Glass kit. FormField's
	// .g-field-error line is the one every Glass form already uses.
	assert.doesNotMatch(src, /<ErrorMessage\b|\bErrorMessage,/, "no frappe-ui ErrorMessage is left")
	const line = src.match(/<p\b[^>]*class="g-field-error[^"]*"[^>]*>[^<]*<\/p>/)?.[0]
	assert.ok(line, "the error is a <p class=g-field-error>")
	assert.match(line, /role="alert"/, "screen readers hear it")
	assert.match(line, /\{\{\s*formError\s*\}\}/, "it prints the form's one error text")
	// text, not v-html: a refusal can carry markup and must reach the reader as words
	assert.doesNotMatch(line, /v-html/)
	// same place as before: inside the save bar, above the primary button
	const bar = src.slice(src.indexOf("<!-- save/submit/cancel -->"))
	assert.ok(bar.indexOf('role="alert"') > 0, "the line sits in the save bar")
	assert.ok(bar.indexOf('role="alert"') < bar.indexOf("<GButton"), "above the button")
})

test("the error text keeps every source it had: validation, insert, save, finalize", () => {
	const block = src.match(/const formError = computed\(\(\) => \{[\s\S]*?\n\}\)/)?.[0]
	assert.ok(block, "formError is one computed")
	for (const source of [
		"formErrorMessage.value",
		"docList?.insert?.error",
		"documentResource?.setValue?.error",
		"finalize.error",
	])
		assert.ok(block.includes(source), `formError reads ${source}`)
	// a failed request is an Error object: reduce it to the server's first sentence
	assert.match(block, /firstMessage\(/)
})
