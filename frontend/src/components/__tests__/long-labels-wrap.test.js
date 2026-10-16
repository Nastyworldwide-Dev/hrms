// alpha.56: text follows the phone's Text Size. At 135% three labels that are
// sentences, not names, were cut off mid-word with "…": Approvals' two "already
// answered" rows and a request's history line ("Not approved by <approver>",
// which carries a person's name). They wrap now; a short menu label still
// keeps its one line.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Approvals' already-answered rows wrap", () => {
	const page = read("../../views/Approvals.vue")
	assert.match(page, /<GListRow :label="requestsAnsweredLabel" wrap /)
	assert.match(page, /<GListRow :label="answeredLabel" wrap /)
})

test("a request's history line wraps: it carries a name and a reason", () => {
	const timeline = read("../RequestTimeline.vue")
	const row = timeline.slice(timeline.indexOf("<GListRow"), timeline.indexOf("</GListRow>"))
	assert.match(row, /\n\s*wrap\n/)
})
