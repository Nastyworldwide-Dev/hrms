// alpha.60 #2 (owner, 20 Oct 2026): each expense line carries its own receipt,
// picked in the item sheet, instead of one file for the whole claim at the
// bottom of the form. The server half is hrms/tests/test_an_expense_line_carries_its_own_receipt.py.
// Source-asserted because the node runner does not compile SFCs (see send-says-why.test.js);
// the file-name helper is imported and run for real.
// Run: cd frontend && node --test src/components/__tests__/receipt-per-line.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { receiptName } from "../../utils/receiptName.js"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const parts = (src) => ({
	src,
	template: src.slice(0, src.indexOf("<script")),
	script: src.slice(src.indexOf("<script"), src.indexOf("</script>")),
})
const row = () => parts(read("../ReceiptRow.vue"))
const table = () => parts(read("../ExpensesTable.vue"))

// ReceiptRow: pick, upload at once, say what is happening

test("ReceiptRow uploads the picked file at once, with no parent, and emits its URL", () => {
	const { script } = row()
	assert.match(script, /import \{ FileAttachment \} from "@\/composables"/)
	assert.match(script, /new FileAttachment\(\w+\)\.upload\(null, null, ""\)/)
	assert.match(script, /emit\("update:url", [\w.]*file_url\)/)
})

test("ReceiptRow: a failed upload keeps the old value (the upload already toasted)", () => {
	const { script } = row()
	const pick = script.slice(script.indexOf("async function pick"))
	const failed = pick.slice(pick.indexOf("catch"), pick.indexOf("finally"))
	assert.ok(failed.length > 5, "the failure is caught")
	assert.doesNotMatch(failed, /emit\(/, "nothing is emitted on failure")
	assert.match(failed, /console\.warn\(/, "and it is logged, not swallowed")
})

test("ReceiptRow: a late upload never lands in the next sheet's item", () => {
	const { script } = row()
	assert.match(script, /onBeforeUnmount\(/)
	assert.match(script, /if \(!alive\) return/)
})

test("ReceiptRow says Uploading while it uploads and tells its parent", () => {
	const { template, script } = row()
	assert.match(template, /__\("Uploading…"\)/)
	assert.match(template, /:disabled="uploading"/)
	assert.match(script, /emit\("update:uploading", true\)/)
	assert.match(script, /emit\("update:uploading", false\)/)
})

test("ReceiptRow: the rule is shown on the row before Add, not only refused at it", () => {
	const { template } = row()
	assert.match(template, /v-else-if="required"[^>]*>\s*\{\{ __\("Required"\) \}\}/)
	assert.match(template, /__\("Tap to replace"\)/)
	assert.match(template, /\{\{ __\("Add a file"\) \}\}/)
	assert.match(template, /:aria-label=/)
})

test("ReceiptRow: the input is reachable by keyboard and a screen reader (g-sr, not hidden)", () => {
	const { template } = row()
	assert.match(template, /<input\s+class="g-sr"\s+type="file"/)
	assert.doesNotMatch(template, /class="hidden"/)
})

test("ReceiptRow: a sent line's receipt opens from a tap, and an empty one shows nothing", () => {
	const { template } = row()
	assert.match(template, /v-if="!readOnly \|\| url"/)
	assert.match(template, /<GAttachmentRow\b[\s\S]*?@open=/)
	assert.match(template, /<FilePreviewModal\b/)
})

test("receiptName reads the file name off the URL", () => {
	assert.equal(receiptName("/private/files/receipt_ab12cd.jpg"), "receipt_ab12cd.jpg")
	assert.equal(receiptName("/private/files/My%20lunch.pdf?x=1"), "My lunch.pdf")
	assert.equal(
		receiptName("/private/files/100%.jpg"),
		"100%.jpg",
		"a malformed escape is shown as it is"
	)
	assert.equal(receiptName(null), "")
	assert.equal(receiptName(""), "")
})

// ExpensesTable: one receipt per line, required per type

test("the item sheet renders ReceiptRow bound to the line's receipt", () => {
	const { template, script } = table()
	assert.match(script, /import ReceiptRow from "@\/components\/ReceiptRow\.vue"/)
	assert.match(template, /<ReceiptRow\b/)
	assert.match(template, /v-model:url="expenseItem\.receipt"/)
	assert.match(template, /:required="lineNeedsReceipt"/)
	assert.match(template, /:readOnly="isReadOnly"/)
	assert.match(template, /v-model:uploading="receiptUploading"/)
})

test("the generic field loop never renders the Attach field", () => {
	const { script } = table()
	assert.match(script, /\.filter\(\(field\) => field\.fieldname !== "receipt"\)/)
})

test("a line needs a receipt unless its type switched it off (a type not loaded yet counts as required)", () => {
	const { script } = table()
	assert.match(
		script,
		/const lineNeedsReceipt = computed\(\s*\(\) => claimTypesByID\[expenseItem\.value\.expense_type\]\?\.receipt_required !== 0/
	)
})

test("Add is dimmed exactly when it says why, linked to the button", () => {
	const { template, script } = table()
	const hint = script.slice(
		script.indexOf("const addHint"),
		script.indexOf("const addButtonDisabled")
	)
	assert.match(hint, /needsReceipt: lineNeedsReceipt\.value/)
	assert.match(hint, /uploading: receiptUploading\.value/)
	assert.match(hint, /loadFailed: Boolean\(expensesTableFields\.error\)/)
	assert.match(script, /const addButtonDisabled = computed\(\(\) => Boolean\(addHint\.value\)\)/)
	assert.match(
		template,
		/<p\s+v-if="addHint"\s+id="expense-add-hint"\s+class="g-form-footer"\s+role="status"/
	)
	assert.match(template, /:aria-describedby="addHint \? 'expense-add-hint' : undefined"/)
})

test("a sheet closed mid-upload does not leave the next Add dimmed", () => {
	const { script } = table()
	const reset = script.slice(
		script.indexOf("function resetSelectedItem"),
		script.indexOf("const expensesTableFields")
	)
	assert.match(reset, /receiptUploading\.value = false/)
})

test("a line that has a receipt says so in the list", () => {
	const { script } = table()
	assert.match(script, /item\.receipt \? __\("Receipt"\)/)
})

// The claim form no longer asks for one file for the whole claim

test("the expense form no longer requires a claim-level attachment", () => {
	const { template, script } = parts(read("../../views/expense_claim/Form.vue"))
	assert.doesNotMatch(template, /requireAttachment/)
	assert.doesNotMatch(script, /receiptRequired/)
	assert.doesNotMatch(script, /claimTypesByID/, "the unused import went with it")
})

test("old claims keep their claim-level files listed; a new claim has no such row", () => {
	const { template } = parts(read("../../views/expense_claim/Form.vue"))
	assert.match(template, /:showAttachmentView="Boolean\(props\.id\)"/)
})

// The approver sees each line's receipt on the line

test("the approver's expense list shows each line's receipt, read-only", () => {
	const { template, script } = parts(read("../ExpenseItems.vue"))
	assert.match(script, /import ReceiptRow from "@\/components\/ReceiptRow\.vue"/)
	assert.match(template, /<ReceiptRow\s+:url="item\.receipt"\s+read-only\s*\/>/)
})
