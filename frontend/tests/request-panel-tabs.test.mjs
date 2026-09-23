import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) =>
	readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const source = read("../src/components/RequestPanel.vue")

// 23 Sep 2026 (AUDIT-PLAN Approvals row + ruling 2): what waits on an
// approver lives on Approvals, so the Requests "Team Requests" tab is cut;
// what they already decided stays reachable, worded for what is behind it.
test("an approver's second tab is what they already answered", () => {
	assert.match(
		source,
		/isApprover\.data\s*\?\s*\[\s*MINE,\s*ANSWERED\s*\]\s*:\s*\[\s*MINE\s*\]/
	)
	assert.match(source, /label: __\("Answered by you"\)/)
	assert.match(source, /__\("You haven't answered any requests yet\."\)/)
	assert.doesNotMatch(source, /"Team Requests"/)
})

test("a vanished active tab falls back instead of rendering a blank panel", () => {
	// The isApprover verdict hydrates from cache and can flip true -> false
	// after paint; a user parked on a vanished tab must not see a blank panel.
	assert.match(source, /watch\(TAB_BUTTONS/)
	assert.match(source, /includes\(activeTab\.value\)/)
	assert.match(source, /activeTab\.value = "mine"/)
})

test("Approvals links to it, and Requests opens on it from ?tab=answered", () => {
	assert.match(
		read("../src/views/Approvals.vue"),
		/name: "Requests", query: \{ tab: "answered" \}/
	)
	// Since the one-screen Requests page (23 Sep), ?tab=answered opens See all
	// on Answered through utils/requestsPage.opensOnAnswered.
	assert.match(source, /opensOnAnswered\(route\.query\)/)
	assert.match(read("../src/utils/requestsPage.js"), /tab === "answered"/)
})

test("no eyebrow repeats the page title (S-EYEBROW)", () => {
	assert.doesNotMatch(source, /class="g-eyebrow mb-4">\s*\{\{ __\("Requests"\) \}\}/)
})
