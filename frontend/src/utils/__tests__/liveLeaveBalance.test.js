// The leave balance the approver reads is the balance the approve is judged by
// (owner screenshot, 23 Sep 2026: sheet said "Leave Balance 1", Approve said
// "Insufficient leave balance"). The stored leave_balance is a snapshot from
// filing; get_decision_actions now returns leave_balance_now, the number
// validate_balance_leaves uses. The sheet shows that one, and says in plain words
// when it is short. Approve stays: the server decides (allow_negative types exist).
// Run: cd frontend && node --test src/utils/__tests__/liveLeaveBalance.test.js
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { shownLeaveBalance, shortLeaveNotice } from "../liveLeaveBalance.js"

const t = (text, args = []) => text.replace(/\{(\d)\}/g, (_, i) => args[i])
const doc = { leave_type: "Birthday Leave", leave_balance: 1, total_leave_days: 1 }

test("the live balance replaces the stored snapshot", () => {
	assert.equal(shownLeaveBalance(doc, 0), 0)
	assert.equal(shownLeaveBalance(doc, 0.5), 0.5)
})

test("with no live balance the stored field is shown", () => {
	assert.equal(shownLeaveBalance(doc, null), 1)
	assert.equal(shownLeaveBalance(doc, undefined), 1)
})

test("short: one plain line naming the type and what is left", () => {
	assert.equal(
		shortLeaveNotice(doc, 0, t),
		"Not enough Birthday Leave left for these dates (0 left)."
	)
	assert.equal(
		shortLeaveNotice({ ...doc, total_leave_days: 2 }, 1.5, t),
		"Not enough Birthday Leave left for these dates (1.5 left)."
	)
})

test("enough, or no live number: nothing to say", () => {
	assert.equal(shortLeaveNotice(doc, 1, t), "")
	assert.equal(shortLeaveNotice(doc, 3, t), "")
	assert.equal(shortLeaveNotice(doc, null, t), "")
	assert.equal(shortLeaveNotice(null, 0, t), "")
})

// Wiring, source-asserted: the node runner does not compile SFCs.
const sheet = readFileSync(
	fileURLToPath(new URL("../../components/RequestActionSheet.vue", import.meta.url)),
	"utf8"
)
const composable = readFileSync(
	fileURLToPath(new URL("../../composables/decisionCapability.js", import.meta.url)),
	"utf8"
)

test("the live number comes from the capability response, not a new request", () => {
	assert.match(composable, /leave_balance_now/)
	assert.doesNotMatch(sheet, /get_leave_balance_on/)
	assert.match(sheet, /decisionCapability\.leaveBalanceNow/)
})

test("the sheet shows the notice above the Approve button and keeps Approve", () => {
	const template = sheet.slice(0, sheet.indexOf("<script"))
	const notice = template.indexOf("leaveShortNotice")
	const approve = template.indexOf("hasPermission('approve')")
	assert.ok(notice > 0 && notice < approve, "notice renders above the Approve button")
	assert.doesNotMatch(template, /v-if="[^"]*hasPermission\('approve'\)[^"]*leaveShortNotice/)
})
