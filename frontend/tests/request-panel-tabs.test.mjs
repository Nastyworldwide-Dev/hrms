import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../src/components/RequestPanel.vue", import.meta.url)),
	"utf8"
)

// The isApprover verdict hydrates from cache asynchronously and can flip
// true -> false after paint. Verified by adversarial review: without a clamp,
// a user parked on "Team Requests" when the tabs shrink hits a template where
// NO v-if branch matches — a blank panel with no way back. These pins keep
// the gate and its safety net together.

test("the team tabs are gated on the approver verdict", () => {
	assert.match(
		source,
		/isApprover\.data\s*\?\s*\["My Requests", "Team Requests", "History"\]/
	)
	assert.match(source, /:\s*\["My Requests"\]/)
})

test("a vanished active tab falls back instead of rendering a blank panel", () => {
	assert.match(source, /watch\(TAB_BUTTONS/)
	assert.match(source, /tabs\.includes\(activeTab\.value\)/)
	assert.match(source, /activeTab\.value = "My Requests"/)
})
