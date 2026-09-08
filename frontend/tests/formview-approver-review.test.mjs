import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const source = read("../src/components/FormView.vue")

// An approver who opened a request from its notification landed on the
// applicant's edit form: no Approve, no Reject, only editable fields. The
// decision lives in RequestActionSheet (Home > Team Requests); the form must
// open that same sheet rather than grow a second approval path.

test("the form offers the approver the decision sheet, not a second approval path", () => {
	assert.match(source, /import RequestActionSheet from "@\/components\/RequestActionSheet\.vue"/)
	assert.match(source, /v-else-if="canReview"/)
	assert.match(source, /<RequestActionSheet[\s\S]*?:showOpenForm="false"[\s\S]*?v-model="reviewRequest"/)
	// no inline approve/reject wiring in the form itself
	assert.doesNotMatch(source, /status: ['"]Approved['"]/)
})

test("review is offered only on someone else's open, unsubmitted request", () => {
	const block = source.slice(source.indexOf("const canReview"), source.indexOf("const showReviewSheet"))
	assert.match(block, /doc\.docstatus === 0/)
	assert.match(block, /\["Open", "Draft"\]\.includes\(doc\[decisionField\]\)/)
	assert.match(block, /doc\.employee !== employee\.data\?\.name/)
	assert.match(block, /permittedWriteFields\.data\?\.includes\(decisionField\)/)
	// Expense Claim decides on approval_status, everything else on status
	assert.match(source, /REVIEW_DECISION_FIELD = \{ "Expense Claim": "approval_status" \}/)
})

test("closing the sheet reloads the document so the form shows the decision", () => {
	assert.match(source, /@didDismiss="closeReviewSheet"/)
	const fn = source.slice(source.indexOf("function closeReviewSheet"))
	assert.match(fn.slice(0, 300), /reloadDoc\(\)/)
})

test("the shared summary-field map covers the doctypes the sheet can decide", () => {
	const fields = read("../src/data/config/requestSummaryFields.js")
	const block = fields.slice(fields.indexOf("export const REQUEST_SUMMARY_FIELDS"))
	for (const dt of ["Leave Application", "Expense Claim", "Shift Request", "Attendance Request", "OT Request"]) {
		assert.match(block, new RegExp(`"${dt}": `))
	}
})
