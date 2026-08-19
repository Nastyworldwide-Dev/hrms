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

test("the entry is gated on the approver verdict", () => {
	assert.match(
		source,
		/v-if="isApprover\.data"[\s\S]{0,120}name: 'RemoteApprovals'/
	)
})

test("the gate is never the pending count", () => {
	assert.doesNotMatch(
		source,
		/v-if="pendingApprovalsCount[\s\S]{0,80}RemoteApprovals/
	)
})
