import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

// A decision changes three surfaces: the queue, the History tab, and the
// pending-count badge on Home/Profile. The realtime event cannot refresh them
// for the deciding approver — the backend publishes the decision to the
// EMPLOYEE — so submitDecision must reload all three itself. This pin exists
// because the original code reloaded only `pending` and the other two went
// stale until manual navigation.
test("deciding reloads queue, history, and the pending badge together", () => {
	const source = readFileSync(
		fileURLToPath(new URL("../src/views/RemoteApprovals.vue", import.meta.url)),
		"utf8"
	)
	assert.match(
		source,
		/Promise\.all\(\[\s*pending\.reload\(\),\s*decided\.reload\(\),\s*pendingCountResource\.reload\(\)\s*,?\s*\]\)/
	)
})
