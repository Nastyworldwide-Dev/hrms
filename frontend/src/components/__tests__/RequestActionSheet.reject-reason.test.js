// Audit P0-10: rejecting asked "are you sure?" and nothing else, so the
// employee never learned why. The reject confirm now asks "Why not?", keeps
// Reject disabled until it is answered, and sends the reason with the
// decision — the server refuses a rejection without one (approval.decide).
// Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(
	fileURLToPath(new URL("../RequestActionSheet.vue", import.meta.url)),
	"utf8"
)
const template = src.slice(0, src.indexOf("<script"))

test("the reject confirm asks why, in the person's words", () => {
	const confirm = template.slice(
		template.indexOf("<!-- Irreversible-action confirm"),
		template.indexOf("<!-- Withdraw own draft")
	)
	assert.match(confirm, /<GTextarea[\s\S]*v-model="rejectReason"/)
	assert.match(confirm, /__\(['"]Why not\?['"]\)/)
})

test("Reject cannot be pressed with an empty reason", () => {
	const confirm = template.slice(
		template.indexOf("<!-- Irreversible-action confirm"),
		template.indexOf("<!-- Withdraw own draft")
	)
	assert.match(confirm, /:confirm-disabled="needsReason && !rejectReason\.trim\(\)"/)
})

test("the reason goes to the server with the decision", () => {
	const at = src.indexOf("return decision.submit(")
	assert.match(src.slice(at, at + 300), /reason: status === "Rejected" \? reason : undefined/)
})
