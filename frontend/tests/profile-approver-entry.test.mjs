import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../src/views/Profile.vue", import.meta.url)),
	"utf8"
)

// The Remote Approvals entry follows the same verdict as the Team tabs:
// visible to people approval work can actually reach, invisible to everyone
// else. Two past mistakes are pinned against here: gating on the pending
// COUNT (the entry vanished when the queue emptied, stranding approvers from
// their History), and no gate at all (every normal employee saw an approvals
// surface that could never apply to them — reported live 2026-08-19).

// 22 Sep 2026: Profile was regrouped (revamp §7) and the row moved from a
// hand-built router-link into the "Work" group, so the v-if became a spread on
// a computed. The RULE is unchanged and is what these now assert — the markup
// shape was never the thing worth pinning, and asserting it meant a layout
// change read as a permission regression.

test("the entry is gated on the approver verdict", () => {
	const row = source.slice(source.indexOf('key: "approvals"'))
	assert.ok(row, "the approvals row exists")
	// The gate sits on the SPREAD that builds the row, so an unentitled user
	// gets no row at all rather than a hidden one.
	const gate = source.slice(
		source.indexOf("isApprover.data"),
		source.indexOf('key: "approvals"')
	)
	assert.match(gate, /\?\s*\[/, "isApprover decides whether the row is built")
	assert.match(
		row,
		/name: "Approvals"/,
		"and it goes to the approvals screen"
	)
})

test("the gate is never the pending count", () => {
	// Count-gating once made the entry vanish the moment the queue emptied,
	// stranding an approver away from their own decision history.
	const gate = source.slice(
		source.indexOf("isApprover.data"),
		source.indexOf('key: "approvals"')
	)
	assert.doesNotMatch(
		gate,
		/pendingApprovalsCount/,
		"the count is not the gate"
	)
	// It is allowed to be the BADGE — that is a number, not a permission.
	const row = source.slice(source.indexOf('key: "approvals"'))
	assert.match(
		row.slice(0, 400),
		/badge:.*pendingApprovalsCount/s,
		"the count is a badge"
	)
})
