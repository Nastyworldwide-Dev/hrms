// E1 (14 Sep 2026): approving a forgotten check-out always toasted "The employee
// has been notified." even when the day stayed Half Day. The toast now says
// whether attendance was updated, and why not when it was not.
// Run: cd frontend && node --test src/utils/__tests__/approvalToast.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

import { decisionToast } from "../approvalToast.js"

const __ = (text, args = []) => text.replace(/\{(\d+)\}/g, (_, i) => String(args[Number(i)]))

test("an applied repair names the new status and hours", () => {
	const toast = decisionToast(
		"approve",
		{ repaired: true, status: "Present", working_hours: 9.5, reason_code: null },
		__
	)
	assert.equal(toast.title, "Approved")
	assert.equal(toast.text, "Attendance updated to Present 9.5h.")
	assert.equal(toast.tone, "success")
})

test("a refused repair says NOT updated, gives the plain reason, and never a raw code", () => {
	const toast = decisionToast(
		"approve",
		{
			repaired: false,
			reason_code: "hr_marked",
			message: "HR marked this day by hand.",
			hr_notified: true,
			will_retry: false,
		},
		__
	)
	assert.equal(toast.title, "Approved")
	assert.match(toast.text, /^Attendance NOT updated: HR marked this day by hand\./)
	assert.match(toast.text, /HR has been told\./)
	assert.doesNotMatch(toast.text, /hr_marked/)
	assert.equal(toast.tone, "warning")
})

test("a retried repair says it will retry instead of blaming HR", () => {
	const toast = decisionToast(
		"approve",
		{
			repaired: false,
			reason_code: "pending_punch",
			message: "Another punch in this shift is still awaiting approval.",
			hr_notified: false,
			will_retry: true,
		},
		__
	)
	assert.match(toast.text, /It will update automatically once that clears\./)
	assert.doesNotMatch(toast.text, /HR has been told/)
})

test("ordinary approvals and rejections keep the notified message", () => {
	assert.equal(decisionToast("approve", null, __).text, "The employee has been notified.")
	const rejected = decisionToast("reject", null, __)
	assert.equal(rejected.title, "Rejected")
	assert.equal(rejected.text, "The employee has been notified.")
})

test("the approver view builds its toast from the approve result", () => {
	const source = readFileSync(new URL("../../views/RemoteApprovals.vue", import.meta.url), "utf8")
	assert.match(source, /decisionToast\(\s*decision\.value,\s*result\?\.attendance_repair/)
})
