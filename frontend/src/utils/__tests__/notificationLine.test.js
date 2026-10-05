// A notification reads as one short line — never a table name, a raw id or a
// timestamp with seconds (owner screenshot, 23 Sep 2026).
import { test } from "node:test"
import assert from "node:assert/strict"
import dayjs from "dayjs"

import { dayGroup, notificationLine } from "../notificationLine.js"

const row = (message, doctype = "Leave Application") => ({
	message,
	reference_document_type: doctype,
	reference_document_name: "HR-LAP-2026-02733",
})

test("a decision reads 'Time off approved' by the approver, nothing else", () => {
	const line = notificationLine(
		row(
			"<b>Your</b> <b>Leave Application</b> HR-LAP-2026-02733 has been <b>Approved</b> by <b>Hafiz Salim</b> on 23-09-2026 18:31:03"
		)
	)
	assert.deepEqual(line, { title: "Time off approved", who: "Hafiz Salim", reason: "" })
})

test("older rows without the date and other kinds read the same way", () => {
	const ot = notificationLine(
		row(
			"<b>Your</b> <b>OT Request</b> HR-OTR-26-09-00066 has been <b>Approved</b> by <b>Hafiz Salim</b>",
			"OT Request"
		)
	)
	assert.deepEqual(ot, { title: "Overtime approved", who: "Hafiz Salim", reason: "" })
	const rejected = notificationLine(
		row(
			"<b>Your</b> <b>Expense Claim</b> HR-EXP-2026-00007 has been <b>Rejected</b> by <b>Administrator</b>",
			"Expense Claim"
		)
	)
	assert.equal(rejected.title, "Expense not approved")
})

test("an approver sees who asked, not the document id", () => {
	const line = notificationLine(
		row(
			"<b>Nurul Aisyah</b> raised a new <b>Leave Application</b> for approval: HR-LAP-2026-02740"
		)
	)
	assert.equal(line.title, "Nurul Aisyah asked for time off")
	assert.doesNotMatch(line.title, /HR-LAP/)
})

test("issue updates drop the id", () => {
	const line = notificationLine(
		row("Your issue <b>HR-ISS-26-09-00002</b> is now <b>Completed</b>", "Employee Issue")
	)
	assert.deepEqual(line, { title: "Issue completed", who: "", reason: "" })
})

test("text already written for people is kept, minus any raw id", () => {
	assert.equal(
		notificationLine(row("You haven't checked in yet. Tap to check in.", "")).title,
		"You haven't checked in yet. Tap to check in."
	)
})

test("remote check-in rows read their decision", () => {
	const line = notificationLine(row("", "Remote Checkin Request"), { remoteStatus: "Pending" })
	assert.equal(line.title, "Check-in outside the area to decide")
})

test("rows group into Today / Yesterday / Earlier on the site clock", () => {
	const now = dayjs("2026-09-23T21:34:00")
	assert.equal(dayGroup(dayjs("2026-09-23T18:31:00"), now), "Today")
	assert.equal(dayGroup(dayjs("2026-09-22T17:54:00"), now), "Yesterday")
	assert.equal(dayGroup(dayjs("2026-09-18T09:00:00"), now), "Earlier")
})

// ---- a rejection now carries the approver's reason (5 Oct 2026) ----
// The server appends ". Reason: <escaped text>" to the stored sentence. The feed reads "who decided" out
// of that sentence, so the reason must not leak into the name, and the reason's HTML entities must be
// shown as the characters they stand for.
const REJECTED = (reason) =>
	`<strong>Your</strong> <strong>Leave Application</strong> HR-LAP-2026-00050 has been <strong>Rejected</strong> by <strong>Hafiz</strong> on 2026-10-05 14:58:41${
		reason === undefined ? "" : `. <strong>Reason</strong>: ${reason}`
	}`

test("a rejection with a reason still names WHO decided, and only who", () => {
	const line = notificationLine({
		message: REJECTED("No cover that week"),
		reference_document_type: "Leave Application",
	})
	assert.equal(line.title, "Time off not approved")
	assert.equal(line.who, "Hafiz")
})

test("the reason is carried separately, with its entities decoded", () => {
	const line = notificationLine({
		message: REJECTED("it&#x27;s &lt;b&gt;busy&lt;/b&gt; &amp; late &quot;sorry&quot;"),
		reference_document_type: "Leave Application",
	})
	assert.equal(line.reason, `it's <b>busy</b> & late "sorry"`)
})

test("a rejection with no reason has an empty reason", () => {
	const line = notificationLine({
		message: REJECTED(),
		reference_document_type: "Leave Application",
	})
	assert.equal(line.reason, "")
	assert.equal(line.who, "Hafiz")
})

test("an approval never has a reason", () => {
	const line = notificationLine({
		message: REJECTED("x").replace("Rejected", "Approved"),
		reference_document_type: "Leave Application",
	})
	assert.equal(line.reason, "")
})

test("other kinds of notice carry an empty reason too", () => {
	const line = notificationLine({
		message:
			"<strong>Aisyah</strong> raised a new <strong>Leave Application</strong> for approval: HR-LAP-1",
		reference_document_type: "Leave Application",
	})
	assert.equal(line.reason, "")
})
