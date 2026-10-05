// The Approvals page's filter, select mode, banner and bulk approve are WIRED to the helpers
// (utils/approvalBulk.js) and to the two server endpoints (hrms.api.approval.check_many /
// decide_many). The helpers have their own tests; this keeps the page from drifting off them.
// HR, 4 Oct 2026; owner, 5 Oct: no export, banner only, phone and desktop.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Approvals.vue", import.meta.url)), "utf8")
const template = page.slice(0, page.indexOf("<script"))
const script = page.slice(page.indexOf("<script"), page.indexOf("<style"))

test("it calls the two bulk endpoints, and nothing else decides in bulk", () => {
	assert.match(script, /hrms\.api\.approval\.check_many/)
	assert.match(script, /hrms\.api\.approval\.decide_many/)
	assert.doesNotMatch(script, /status:\s*["']Rejected["']/, "reject stays one by one")
})

test("the filter narrows the groups, so every count follows it", () => {
	assert.match(script, /filterByKind\(rows\.value, kindFilter\.value\)/)
	assert.match(script, /groupApprovals\(visibleRows\.value\)/)
	assert.match(template, /aria-pressed/, "a chip says whether it is on")
})

test("what is sent is the ticked rows with the revision the approver saw", () => {
	assert.match(script, /itemsFor\(ticked\.value, rows\.value\)/)
})

test("only what the check said would go through is approved", () => {
	assert.match(script, /decideMany\.submit\(\{ items: current\.ready \}\)/)
})

test("the confirm sheet says ready and refused, with the reason, and refused ones stay", () => {
	assert.match(template, /__\("\{0\} ready"/)
	assert.match(template, /__\("\{0\} will be refused"/)
	assert.match(template, /:sublabel="req\.reason"/)
	assert.match(template, /Refused ones stay in your list/)
})

test("over the cap is caught before the server is asked", () => {
	assert.match(script, /overCap\(ticked\.value\)/)
})

test("a check-in is never ticked: select mode lists only what can be decided in bulk", () => {
	assert.match(template, /person\.rows\.some\(canBulk\)/)
	assert.match(script, /pickable = computed\(\(\) => visibleRows\.value\.filter\(canBulk\)\)/)
})

test("the banner is a banner: it blocks nothing and forces nothing", () => {
	assert.match(template, /<GBanner v-if="headline"/)
	assert.match(template, /Staff attendance and pay wait on your decision/)
	assert.doesNotMatch(template, /overdue-gate|mandatory|blocking/i)
})

test("an age is a number AND a word, never colour alone", () => {
	assert.match(script, /__\("Today"\)/)
	assert.match(script, /__\("\{0\} days", \[days\]\)/)
})

test("the open-request sheet and the ticked set are different things", () => {
	assert.match(script, /const ticked = ref\(new Set\(\)\)/)
	assert.match(script, /const selected = ref\(null\)/)
})

test("there is no export", () => {
	assert.doesNotMatch(page, /export(?!\s+(default|const|function|async))[^\n]*(csv|excel|xlsx)/i)
	assert.doesNotMatch(template, />\s*Export\s*</)
})

test("the sticky bar names how many and checks first", () => {
	assert.match(template, /__\("\{0\} selected"/)
	assert.match(template, /Each one is checked before it is approved/)
})

test("the empty line shows only when nothing waits, never above a queue", () => {
	// it hung off a v-else; inserting the select-all row between the pair moved the else
	const at = template.indexOf("Nothing is waiting on you")
	const opening = template.lastIndexOf("<GListPanel", at)
	assert.match(template.slice(opening, at), /^<GListPanel v-if="!rows\.length"/)
	assert.doesNotMatch(
		template,
		/<GListPanel v-else>\s*<GListRow\s+:label="__\('Nothing is waiting on you/
	)
})

test("the chip that is on has readable colours: both come from tokens that exist", () => {
	const style = page.slice(page.indexOf("<style"))
	const on = style.slice(style.indexOf(".g-approvals__chip--on"))
	const rule = on.slice(0, on.indexOf("}"))
	for (const token of rule.match(/var\((--g-[a-z0-9-]+)\)/g) || []) {
		const name = token.slice(4, -1)
		const defined = readFileSync(
			fileURLToPath(new URL("../../theme/glass.css", import.meta.url)),
			"utf8"
		)
		assert.ok(defined.includes(`${name}:`), `${name} is not defined in the theme`)
	}
})

test("ages and the banner count from the site's calendar day, never the UTC date", () => {
	assert.match(script, /siteToday\(new Date\(\), siteTimeZone\(\)\)/)
	assert.doesNotMatch(script, /toISOString\(\)\.slice\(0, 10\)/)
})
