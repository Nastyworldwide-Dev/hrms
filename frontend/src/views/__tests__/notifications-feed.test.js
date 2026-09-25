// Notifications, alpha.5 (owner, 23 Sep 2026: "drowned with information").
// Each row was the server's whole sentence — "Your Leave Application
// HR-LAP-2026-02733 has been Approved by Hafiz Salim on 23-09-2026 18:31:03"
// — rendered raw with v-html, under a huge "{0} Unread" number. The screen now
// reads one short line per row (utils/notificationLine.js), grouped by day.
// Source-level pins, like the other tests in this directory.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { parse } from "@vue/compiler-sfc"

const page = readFileSync(fileURLToPath(new URL("../Notifications.vue", import.meta.url)), "utf8")
const { template, scriptSetup } = parse(page).descriptor
const markup = template.content
const script = scriptSetup.content

test("the stored message is never rendered raw", () => {
	assert.doesNotMatch(markup, /v-html/, "no v-html anywhere on the feed")
	assert.doesNotMatch(script, /safeHtml/, "nothing left to sanitise: the message is not drawn")
	assert.doesNotMatch(markup, /item\.message/, "the row reads notificationLine, not the sentence")
	assert.match(script, /notificationLine\(/)
})

test("rows are grouped by day, one panel per group", () => {
	assert.match(script, /dayGroup\(\s*siteTime\(/, "the group is the SITE day")
	assert.match(markup, /v-for="group in groups"/)
	assert.match(markup, /<GListPanel[\s\S]*?<GListRow[\s\S]*?v-for="item in group\.items"/)
	for (const word of ["Today", "Yesterday", "Earlier"]) {
		assert.ok(script.includes(`"${word}"`), `${word} is a group`)
	}
})

test("mark all read is a header action; the unread count is a caption, not a stat", () => {
	assert.match(markup, /<template #actions>[\s\S]*?__\("Mark all read"\)[\s\S]*?<\/template>/)
	assert.doesNotMatch(markup, /text-stat-number/)
	assert.doesNotMatch(markup, /\{0\} Unread/)
	// alpha.9 D3: the count rides on the first section header ("Today · 3
	// unread"), not a loose caption above the list.
	assert.match(script, /__\("\{0\} · \{1\} unread"/)
	assert.doesNotMatch(script, /\bButton\b.*frappe-ui|from "frappe-ui"[^\n]*\bButton\b/)
})

test("twenty a page, with Show more, and skeleton rows on the first load", () => {
	assert.match(script, /const pageLength = 20/)
	assert.match(markup, /class="g-focusable g-list-more[^"]*"[^>]*@click="loadMore"/)
	assert.match(markup, /__\("Show more"\)/)
	assert.match(markup, /<GListPanel[^>]*:loading="firstLoad"/)
})

test("a remote check-in status that cannot be read is simply unknown", () => {
	// approvers may not READ Remote Checkin Request; that must not toast
	assert.match(script, /resourceFetcher: frappeRequest/)
})
