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
	// The label is formatHours(d.hours) as given; the form passes hours-as-time.
	assert.equal(open.label, "2")
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

test("the form renders the reason, and says HR handles unclaimable days", () => {
	assert.match(src, /d\.reason/, "the reason is rendered under the date")
	// alpha.6 C3: unclaimable days are folded rows, not buttons, under a footer
	// in plain words (was an "HR can see this" tag on each card).
	assert.match(src, /HR will sort these out/, "the footer says HR handles them")
	assert.match(src, /dayGroups\.cannot/, "unclaimable days are their own folded group")
})

test("the inline field error goes through the deferred helper, the grey hint does not", () => {
	assert.match(src, /field\.error_message = inlineError\.value/)
	// alpha.7 0.5: the grey hint is the Pick-a-day group footer (dayFooter).
	assert.match(src, /<p class="g-form-footer" role="status">\{\{ dayFooter \}\}<\/p>/, "the grey hint is the group footer")
})

// alpha.6 C3 (owner screenshots, 24 Sep 2026): "Claim overtime page shows a
// long list ... to the bottom, killing the idea of compact, no scrolling".
// Every past day was a full card, claimed and unclaimable included. NN/g
// (infinite scrolling; accordions): show the few that matter, fold the rest,
// offer "Show more". Open days first (up to 5), then two folded groups.
import { claimDayGroups } from "../claimEmptyReason.js"

const row = (date, extra = {}) => ({ date, disabled: false, label: "1 h", ...extra })

test("open days first, at most 5 until the person asks for more", () => {
	const rows = ["09-20", "09-19", "09-18", "09-17", "09-16", "09-15", "09-14"].map((d) => row(`2026-${d}`))
	const g = claimDayGroups(rows)
	assert.equal(g.open.length, 5)
	assert.equal(g.moreOpen, 2)
	assert.equal(claimDayGroups(rows, { showAll: true }).open.length, 7)
})

test("claimed and unclaimable days are counted and folded, not listed", () => {
	const rows = [
		row("2026-09-20"),
		row("2026-09-19", { claimed: true, disabled: true }),
		row("2026-09-18", { claimed: true, disabled: true }),
		row("2026-09-17", { incomplete: true, disabled: true, reason: "Only a check-in" }),
	]
	const g = claimDayGroups(rows)
	assert.deepEqual(g.open.map((r) => r.date), ["2026-09-20"])
	assert.equal(g.claimed.length, 2)
	assert.equal(g.cannot.length, 1)
})

// alpha.7 0.3 (owner's live shot): "Checking overtime for this date…" showed in
// RED inside the Hours row. Loading is not an error. The inline (red) channel
// carries errors only; the loading state is shown as progress, not as a problem.
import { inlineClaimError as inlineErr } from "../claimEmptyReason.js"
test("a pending check is never shown as a red error", () => {
	assert.equal(inlineErr("Checking overtime for this date…", { hasDate: true, loading: true }), "")
	assert.equal(inlineErr("Enter the hours to claim.", { hasDate: true, loading: false }), "Enter the hours to claim.")
})

// alpha.7 0.2: the live "Could not check overtime" could not be reproduced; the
// form threw the server's reason away. It now shows it, so the next report
// names the cause instead of a generic line.
import { summaryFailure } from "../claimEmptyReason.js"
test("a failed check says the server's own reason when there is one", () => {
	const __ = (s, a) => (a ? s.replace("{0}", a[0]) : s)
	assert.equal(
		summaryFailure({ messages: ["Attendance for 23 Sep is not submitted yet"] }, __),
		"Could not check overtime: Attendance for 23 Sep is not submitted yet"
	)
	assert.equal(summaryFailure({}, __), "Could not check overtime. Try again.")
	assert.equal(summaryFailure({ messages: ["<b>HTML</b> kept out"] }, __), "Could not check overtime: HTML kept out")
})
