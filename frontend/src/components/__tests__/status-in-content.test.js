// alpha.14 H (27 Sep 2026 sweep): a sent request's status sat in the
// navigation bar beside the title, as coloured words that truncated
// ("Approved, not …" on an expense). An iOS navigation bar holds the title
// and controls; the state of the thing on screen is content. The status is
// now the first line of the page, whole; the bar keeps Back, the title
// and the ⋯ menu.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const form = readFileSync(fileURLToPath(new URL("../FormView.vue", import.meta.url)), "utf8")

test("the bar carries no status", () => {
	const actions = form.slice(form.indexOf("#actions>"), form.indexOf("</ShellHeader>"))
	assert.doesNotMatch(actions, /<GStatusChip/)
})

test("the status is the first line of the content, before the fields", () => {
	const content = form.slice(form.indexOf("</ShellHeader>"))
	const chip = content.indexOf('<p v-if="id && status" class="g-form-status">')
	assert.ok(chip > 0, "a status line in the content")
	assert.ok(chip < content.indexOf('<slot name="beforeFields">'))
})
