// An approver is guided, never errored (owner, 29 Sep 2026: "we dont want to
// show error to approver. our system must guide everyone who uses nadi pwa").
// The server dry-runs the Approve (hrms.api.approval.get_decision_actions):
// when it would refuse, Approve is not offered and `blocked` says why and
// what to do. This sheet shows that note where Approve would be, keeps
// Reject, and reloads by itself when the request changed underneath.
// Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const sheet = read("../RequestActionSheet.vue")
const composable = read("../../composables/decisionCapability.js")
const template = sheet.slice(0, sheet.indexOf("<script"))

test("the server's guidance reaches the sheet from the same answer as the buttons", () => {
	assert.match(composable, /const blocked = computed\(\(\) => fresh\.value\?\.blocked \|\| null\)/)
	assert.match(composable, /return \{ actions, leaveBalanceNow, blocked \}/)
})

test("the note sits where Approve would be, with Reject beside it", () => {
	const note = template.indexOf('v-if="approveBlocked"')
	const reject = template.indexOf("hasPermission('reject')")
	assert.ok(note > 0, "the note is drawn")
	assert.ok(note < reject, "above the buttons, so it is read before Reject")
	assert.match(template, /\{\{ approveBlocked\.message \}\}/, "the server's plain words")
	assert.match(template, /role="status"/, "announced, not only shown")
})

test("a changed request reloads by itself instead of a red toast", () => {
	const stale = sheet.slice(sheet.indexOf("useDecisionCapability("), sheet.indexOf("const decision = createResource"))
	assert.doesNotMatch(stale, /variant: "error"/, "no error toast for a changed request")
	assert.match(stale, /document\.reload\?\.\(\)/, "it reloads the request")
})
