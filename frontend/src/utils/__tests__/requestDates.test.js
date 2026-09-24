// The approver's sheet must say WHEN. Found by the alpha.6 screen journey
// (24 Sep 2026): the Fix a day and Shift change sheets showed a reason and a
// name but no date, because their date lines (attendance_dates, shift_dates,
// leave_dates) are computed by the requester's LIST transforms, and the sheet
// opened from Approvals loads the raw document, which has none of them.
import { test } from "node:test"
import assert from "node:assert/strict"

import { requestDates } from "../requestDates.js"

test("time off: one day, and a range", () => {
	assert.equal(requestDates({ doctype: "Leave Application", from_date: "2026-10-14", to_date: "2026-10-14" }), "Wed 14 Oct")
	assert.equal(
		requestDates({ doctype: "Leave Application", from_date: "2026-10-14", to_date: "2026-10-16" }),
		"Wed 14 Oct – Fri 16 Oct"
	)
})

test("fix a day and shift change read the same from/to fields", () => {
	assert.equal(requestDates({ doctype: "Attendance Request", from_date: "2026-09-18", to_date: "2026-09-18" }), "Fri 18 Sep")
	assert.equal(requestDates({ doctype: "Shift Request", from_date: "2026-10-19", to_date: "2026-10-20" }), "Mon 19 Oct – Tue 20 Oct")
})

test("a shift change with no end runs on", () => {
	assert.equal(requestDates({ doctype: "Shift Request", from_date: "2026-10-19", to_date: null }), "From Mon 19 Oct")
})

test("overtime and time off in lieu name their own day fields", () => {
	assert.equal(requestDates({ doctype: "OT Request", ot_date: "2026-09-14" }), "Mon 14 Sep")
	assert.equal(
		requestDates({ doctype: "Compensatory Leave Request", work_from_date: "2026-07-25", work_end_date: "2026-07-26" }),
		"Sat 25 Jul – Sun 26 Jul"
	)
})

test("nothing to say is an empty string, never 'Invalid Date'", () => {
	assert.equal(requestDates({ doctype: "Leave Application" }), "")
	assert.equal(requestDates({ doctype: "Expense Claim", posting_date: "2026-09-24" }), "")
	assert.equal(requestDates(null), "")
})
