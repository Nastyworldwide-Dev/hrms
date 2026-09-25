// alpha.9 R1 "everything in a group" (measured by e2e/ios-consistency-audit.mjs,
// rule 8): only section headers and footers sit outside a group, as in iOS
// Settings. D3 Notifications, D4 Who to ask, D9 You.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("D4 Who to ask: an empty answer is a row in the group, under its header", () => {
	const src = read("../WhoToAsk.vue")
	assert.match(src, /<h2 class="g-form-section__title">\{\{ __\("Your manager"\) \}\}<\/h2>/)
	assert.match(src, /<h2 class="g-form-section__title">\{\{ __\("HR"\) \}\}<\/h2>/)
	assert.match(src, /<GListRow :label="NO_MANAGER" :tappable="false" \/>/)
	assert.match(src, /<GListRow :label="NO_HR" :tappable="false" \/>/)
	assert.match(src, /const NO_MANAGER = __\("No manager is set for you\."\)/)
	assert.match(src, /const NO_HR = __\("HR hasn't listed contacts yet\."\)/)
	assert.doesNotMatch(src, /g-empty-line|class="g-eyebrow/)
})

test("D3 Notifications: the unread count is the section header, not a loose line", () => {
	const src = read("../../views/Notifications.vue")
	assert.doesNotMatch(src, /<span v-if="unreadNotificationsCount\.data" class="text-caption/)
	assert.match(src, /class="g-form-section__title[^"]*">\s*\{\{ groupTitle\(group\) \}\}/)
})

test("D9 You: the version is the last group's footer", () => {
	const src = read("../../views/Profile.vue")
	assert.doesNotMatch(src, /<p class="text-caption text-ink-600 text-center">/)
	assert.match(src, /<p class="g-form-footer g-form-footer--center">\s*\{\{ __\("Version \{0\} · \{1\}"/)
})
