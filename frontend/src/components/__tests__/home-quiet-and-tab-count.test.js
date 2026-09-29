// Quiet when nothing is happening, and approvers find their queue (owner, 29
// Sep 2026, alpha.20 plan D). Home showed "Nothing waiting on you." to every
// approver every day; that box is gone when the queue is empty. Approvers see
// how many requests wait on them on the Requests tab, so the queue no longer
// lives only under More → Your team → Approvals.
// Supersedes the 23 Sep "always show Needs you to an approver" rule.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Needs you shows only when something waits", () => {
	const src = read("../NeedsYou.vue")
	// a failed read still shows, so an approver is never wrongly told "done"
	assert.match(src, /<div v-if="rows\.length \|\| needsYouResource\.error \|\| \(isApprover\.data && firstRead\)" class="w-full">/)
	assert.doesNotMatch(src, /v-if="rows\.length \|\| isApprover\.data"/)
	const template = src.slice(0, src.indexOf("<script")).replace(/<!--[\s\S]*?-->/g, "")
	assert.doesNotMatch(template, /Nothing waiting on you/, "no box that says nothing")
})

test("the Requests tab carries the approver's waiting count", () => {
	const tabs = read("../BottomTabs.vue")
	assert.match(tabs, /v-if="countFor\(item\)"\s+class="g-tabbar__badge"/)
	assert.match(tabs, /item\.route !== "\/requests"/, "Requests only")
	assert.match(tabs, /needsYouResource\.data\?\.total/)
	// spoken, not only drawn
	assert.match(tabs, /:aria-label="countFor\(item\) \?/)
})

test("the badge is a Glass token, not a hard-coded red", () => {
	const css = read("../../theme/glass-components.css")
	const rule = css.match(/\.g-tabbar__badge\s*\{[^}]*\}/)?.[0] || ""
	assert.match(rule, /background: var\(--g-/)
	assert.doesNotMatch(rule, /#[0-9a-f]{3,6}/i)
})
