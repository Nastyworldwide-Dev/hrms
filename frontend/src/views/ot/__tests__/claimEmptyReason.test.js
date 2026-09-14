// An unclaimable day is shown greyed with its reason instead of vanishing.
//
// Goal G2 of the attendance recovery plan. "Days you can claim" listed only
// the days with claim capacity, so a lone check-in, a tap never attached to a
// shift or a punch still waiting for approval simply disappeared — and the
// employee read the gap as lost overtime. The backend now returns those days
// as `incomplete` with a plain reason; the form shows them greyed, not
// selectable, with the reason under the date and an "HR can see this" tag.
// The employee still files the request themselves; nothing here asks them to
// fix a record.
//
// The row shaping is a pure function (node-testable); the markup is
// source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { claimDayRows, emptyClaimReason, inlineClaimError } from "../claimEmptyReason.js"

const __ = (text, args = []) => text.replace(/\{(\d+)\}/g, (_m, i) => args[i])
const chip = (d) => (d.docstatus === 1 ? "Approved" : "Pending")
const opts = { isRL: false, rlHoursPerDay: 8, translate: __, statusLabel: chip }

const summary = {
	compensation: "Overtime Pay",
	days: [{ date: "2026-09-29", hours: 2 }],
	claimed: [{ date: "2026-09-20", hours: 1, status: "Open", docstatus: 0 }],
	incomplete: [
		{
			date: "2026-09-21",
			reason_code: "no_checkout",
			reason: "Only a check-in was recorded for this date (no check-out).",
		},
		{ date: "2026-09-25", reason_code: "pending_approval", reason: "Waiting for approval." },
	],
	days_already_claimed: 1,
	days_with_overtime: 1,
}

test("incomplete days sit in the list, greyed, with their reason, newest first", () => {
	const rows = claimDayRows(summary, opts)
	assert.deepEqual(
		rows.map((r) => r.date),
		["2026-09-29", "2026-09-25", "2026-09-21", "2026-09-20"]
	)
	const lone = rows.find((r) => r.date === "2026-09-21")
	assert.equal(lone.incomplete, true)
	assert.equal(lone.disabled, true, "not selectable")
	assert.match(lone.reason, /no check-out/)
	assert.match(lone.label, /HR can see this/)
})

test("claimable and claimed rows are untouched by the new list", () => {
	const rows = claimDayRows(summary, opts)
	const open = rows.find((r) => r.date === "2026-09-29")
	assert.equal(open.disabled, false)
	assert.equal(open.label, "2 h")
	const claimed = rows.find((r) => r.date === "2026-09-20")
	assert.equal(claimed.disabled, true)
	assert.equal(claimed.label, "Claimed · Pending")
})

test("replacement leave still drops days under the threshold but keeps incomplete ones", () => {
	const rows = claimDayRows(
		{ ...summary, compensation: "Replacement Leave", days: [{ date: "2026-09-29", hours: 2 }] },
		{ ...opts, isRL: true }
	)
	assert.deepEqual(
		rows.map((r) => r.date),
		["2026-09-25", "2026-09-21", "2026-09-20"]
	)
})

test("a summary without the field (older server) renders as before", () => {
	const { incomplete: _dropped, ...older } = summary
	assert.deepEqual(
		claimDayRows(older, opts).map((r) => r.date),
		["2026-09-29", "2026-09-20"]
	)
})

test("when only incomplete days exist the empty-state names them and HR", () => {
	const reason = emptyClaimReason(
		{ ...summary, days: [], claimed: [], days_already_claimed: 0, days_with_overtime: 0 },
		opts
	)
	assert.match(reason, /2 day/)
	assert.match(reason, /HR/)
	assert.doesNotMatch(reason, /no overtime recorded/i)
})

test("with claimable days the empty-state stays silent even if incomplete days exist", () => {
	assert.equal(emptyClaimReason(summary, opts), "")
})

// E9-UX: the red "Choose a work date…" error appeared under Claimed hours the
// moment the form opened — before the employee had done anything wrong.
test("the date error is held back until the date is touched or a save is tried", () => {
	const msg = "Choose a work date to check available overtime."
	assert.equal(inlineClaimError(msg, { hasDate: false, touched: false, saveAttempted: false }), "")
	assert.equal(inlineClaimError(msg, { hasDate: false, touched: true, saveAttempted: false }), msg)
	assert.equal(inlineClaimError(msg, { hasDate: false, touched: false, saveAttempted: true }), msg)
	// once a date is in, every other error shows at once
	assert.equal(
		inlineClaimError("Enter the hours to claim.", { hasDate: true }),
		"Enter the hours to claim."
	)
})

const src = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")

test("the form renders the reason and the HR tag on incomplete rows", () => {
	assert.match(src, /d\.incomplete/, "rows carry the incomplete flag")
	assert.match(src, /d\.reason/, "the reason is rendered under the date")
	assert.match(src, /HR can see this/, "the tag is in the markup or the label")
	assert.match(src, /:disabled="d\.disabled"/, "greyed rows are not selectable")
})

test("the inline field error goes through the deferred helper, the grey hint does not", () => {
	assert.match(src, /field\.error_message = inlineError\.value/)
	assert.match(src, /<p v-if="saveError"/, "the grey hint under the panel stays")
})
