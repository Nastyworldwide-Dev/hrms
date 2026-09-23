// A check-in outside the work area is decided on the Approvals page, in the
// one list (AUDIT-PLAN, Approvals row: "check-ins outside the area" fold in;
// the Remote approvals page and its More and Profile rows are cut).
// The sheet shows what the approver needs — who, when, how far, the photo,
// the employee's reason — and follows the one decision rule: Approve in one
// tap, "Not approve" needs a reason (P0-10).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const sheet = read("../CheckinDecisionSheet.vue")
const page = read("../../views/Approvals.vue")

test("the sheet shows the photo and the employee's reason", () => {
	assert.match(sheet, /row\.selfie_image/)
	assert.match(sheet, /row\.reason/)
})

test("not approving needs a reason; approving does not", () => {
	assert.match(sheet, /__\(['"]Why not\? \(required\)['"]\)/)
	assert.match(sheet, /:confirm-disabled="!reason\.trim\(\)"/)
	assert.match(sheet, /approveResource\.submit\(\{\s*request: props\.row\.name/)
	assert.match(
		sheet,
		/rejectResource\.submit\(\{\s*request: props\.row\.name,\s*approver_remarks: reason\.value\.trim\(\)/
	)
})

test("the Approvals page opens it for check-in rows and the request sheet for the rest", () => {
	assert.match(page, /<CheckinDecisionSheet/)
	assert.match(page, /selected\?\.doctype === 'Remote Checkin Request'/)
})

test("check-ins already answered stay reachable from Approvals (ruling 2)", () => {
	// The old page's "Decided by you" tab was the only place a decided check-in
	// could be reviewed; folding the queue in must not lose it. Plain words
	// (AUDIT-PLAN Wording table): say what is behind the link.
	assert.match(page, /__\("Check-ins you've already answered"\)/)
	assert.match(page, /decidedForApproverResource/)
})

test("the check-in time is shown as the server wrote it, never re-parsed", () => {
	// Review of 52cc288ef: the server sends "Fri 18 Sep, 8:05 am"; running it
	// through dayjs again rendered "Invalid Date" on the one line the approver
	// judges the punch by.
	assert.match(sheet, /\{\{ row\.when \}\}/)
	assert.doesNotMatch(sheet, /\$dayjs\(props\.row\.when\)/)
})

test("the answered link is a full-size row, not a small text button (44px target)", () => {
	assert.doesNotMatch(page, /<button[^>]*openAnswered|@click="openAnswered"[^>]*text-caption/)
	assert.match(page, /<GListRow :label="answeredLabel" @click="openAnswered"/)
})
