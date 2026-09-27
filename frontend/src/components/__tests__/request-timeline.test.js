// alpha.13 slice 1: a sent request shows its story under it — "Sent", then
// each decision with who and when, a "not approved" step with the reason
// (owner ruling R5). Names only; the server gives names, never logins.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { timelineLine } from "../../utils/requestTimeline.js"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const __ = (s, args = []) => s.replace(/\{(\d)\}/g, (_, i) => args[i])

test("each step reads as one plain line", () => {
	assert.equal(timelineLine({ what: "sent", who: "W0 employee" }, __), "Sent by W0 employee")
	assert.equal(timelineLine({ what: "approved", who: "W0 approver" }, __), "Approved by W0 approver")
	assert.equal(timelineLine({ what: "rejected", who: "W0 approver" }, __), "Not approved by W0 approver")
	assert.equal(timelineLine({ what: "cancelled", who: "W0 employee" }, __), "Cancelled by W0 employee")
})

test("a step with no known name says what happened, never a login", () => {
	assert.equal(timelineLine({ what: "approved", who: null }, __), "Approved")
})

test("the timeline is on every sent request, read from the fenced endpoint", () => {
	const form = read("../FormView.vue")
	assert.match(form, /<RequestTimeline\s+v-if="props\.id"/)
	const tl = read("../RequestTimeline.vue")
	assert.match(tl, /hrms\.api\.request_history\.get_request_history/)
	assert.match(tl, /<GListPanel/)
	assert.match(tl, /step\.note/)
})
