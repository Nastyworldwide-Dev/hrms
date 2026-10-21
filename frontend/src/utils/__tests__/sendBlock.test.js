// A dimmed Send always says why (UX review 21 Oct 2026, F1/F4; the #4855 class).
// Run: cd frontend && node --test src/utils/__tests__/sendBlock.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { expenseSendBlock, noApproverReason } from "../sendBlock.js"

const __ = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => String(args[i]))
const NO_APPROVER = { is_mandatory: 1, expense_approver: null }
const HAS_APPROVER = { is_mandatory: 1, expense_approver: "boss@example.com" }

test("no approver where one is required names HR", () => {
	assert.equal(
		noApproverReason(NO_APPROVER, "expense_approver", __),
		"No one is set to approve this for you yet. Ask HR to set your approver."
	)
})

test("an approver that is optional, or set, blocks nothing", () => {
	assert.equal(noApproverReason({ is_mandatory: 0 }, "expense_approver", __), "")
	assert.equal(noApproverReason(HAS_APPROVER, "expense_approver", __), "")
	// still loading: no verdict yet, so no false alarm
	assert.equal(noApproverReason(undefined, "expense_approver", __), "")
})

test("an expense with no lines asks for one; the approver comes first", () => {
	assert.equal(expenseSendBlock({ expenses: [] }, HAS_APPROVER, __), "Add at least one expense.")
	assert.match(expenseSendBlock({ expenses: [] }, NO_APPROVER, __), /Ask HR/)
	assert.equal(expenseSendBlock({ expenses: [{ amount: 5 }] }, HAS_APPROVER, __), "")
})

test("FormView links the reason to Send for a screen reader", () => {
	const src = readFileSync(fileURLToPath(new URL("../../components/FormView.vue", import.meta.url)), "utf8")
	assert.match(src, /id="form-send-reason"/)
	assert.match(src, /:aria-describedby="sendReason \? 'form-send-reason' : undefined"/)
})

test("Time off and Expense both hand their reason to Send", () => {
	const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
	assert.match(read("../../views/leave/Form.vue"), /noApproverReason\(leaveApprovalDetails\.data, 'leave_approver'/)
	assert.match(read("../../views/expense_claim/Form.vue"), /expenseSendBlock\(expenseClaim, expenseApproverDetails\.data/)
	assert.match(read("../../components/ExpensesTable.vue"), /:label="__\('Add expense'\)"/)
})
