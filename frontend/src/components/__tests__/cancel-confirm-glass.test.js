// alpha.7 Phase 4 (plan §5.6): every confirmation is the one Glass alert
// (GConfirm). The last frappe-ui Dialog — "Cancel this request?" with No /
// Yes buttons — goes. The destructive action names itself ("Cancel
// request"); the way out must not also say "Cancel", so it is "Keep request".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const form = readFileSync(fileURLToPath(new URL("../FormView.vue", import.meta.url)), "utf8")

test("no frappe-ui Dialog is left", () => {
	assert.doesNotMatch(form, /<Dialog\b/)
	assert.doesNotMatch(form, /\bDialog,/)
})

test("cancelling a request asks in the Glass alert, with plain buttons", () => {
	const at = form.indexOf(':is-open="showCancelDialog"')
	assert.ok(at > 0)
	const block = form.slice(form.lastIndexOf("<GConfirm", at), form.indexOf("</GConfirm>", at))
	assert.match(block, /:confirm-label="__\('Cancel request'\)"/)
	assert.match(block, /:cancel-label="__\('Keep request'\)"/)
	assert.match(block, /destructive/)
	assert.match(block, /@confirm="handleDocUpdate\('cancel'\)"/)
})

test("the ⋯ menu is the Glass action sheet, Delete in red", () => {
	assert.doesNotMatch(form, /<Dropdown\b/)
	assert.match(form, /<GIconButton\s+:label="__\('More'\)"[\s\S]{0,120}@click="menuOpen = true"/)
	assert.match(form, /<GActionSheet[\s\S]{0,200}:actions="menuActions"/)
	assert.match(form, /key: "delete"[\s\S]{0,80}destructive: true/)
})
