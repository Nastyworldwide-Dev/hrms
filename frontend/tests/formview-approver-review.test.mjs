import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) =>
	readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const source = read("../src/components/FormView.vue")

// An approver who opened a request from its notification landed on the
// applicant's edit form: no Approve, no Reject, only editable fields. The
// decision lives in RequestActionSheet (Home > Team Requests); the form must
// open that same sheet rather than grow a second approval path.

test("the form offers the approver the decision sheet, not a second approval path", () => {
	assert.match(
		source,
		/import RequestActionSheet from "@\/components\/RequestActionSheet\.vue"/
	)
	assert.match(source, /v-else-if="canReview"/)
	assert.match(
		source,
		/<RequestActionSheet[\s\S]*?:showOpenForm="false"[\s\S]*?v-model="reviewRequest"/
	)
	// no inline approve/reject wiring in the form itself
	assert.doesNotMatch(source, /status: ['"]Approved['"]/)
})

// Capability, self-action and dirty-state behavior run against actual Vue and
// installed Frappe resources in decision-capability.test.mjs.

test("closing the sheet reloads the document so the form shows the decision", () => {
	assert.match(source, /@didDismiss="closeReviewSheet"/)
	const fn = source.slice(source.indexOf("function closeReviewSheet"))
	assert.match(fn.slice(0, 300), /reloadDoc\(\)/)
})

test("the shared summary-field map covers the doctypes the sheet can decide", () => {
	const fields = read("../src/data/config/requestSummaryFields.js")
	const block = fields.slice(
		fields.indexOf("export const REQUEST_SUMMARY_FIELDS")
	)
	for (const dt of [
		"Leave Application",
		"Expense Claim",
		"Shift Request",
		"Attendance Request",
		"OT Request",
		"Replacement Leave Claim",
	]) {
		assert.match(block, new RegExp(`"${dt}": `))
	}
})
