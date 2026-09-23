// The Requests page fits one phone screen (owner-approved layout, 23 Sep 2026):
// New request, one balances line, needs attention, your last 5, See all.
// Pure helpers are tested by running them; the page layout by reading source
// (no SFC compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import {
	balancesLine,
	lastRequests,
	LAST_ROWS,
	opensOnAnswered,
	shortLeaveName,
	trimNumber,
} from "../requestsPage.js"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const template = (text) => text.slice(0, text.indexOf("<script"))
const noComments = (text) => text.replace(/<!--[\s\S]*?-->/g, "")

// ---------------------------------------------------------------- pure parts

test("a balance number is trimmed: 6, not 6.0; 12.5 stays", () => {
	assert.equal(trimNumber(6), "6")
	assert.equal(trimNumber("6.0"), "6")
	assert.equal(trimNumber(12.5), "12.5")
	assert.equal(trimNumber(0), "0")
})

test("a leave name drops the trailing word 'Leave'", () => {
	assert.equal(shortLeaveName("Annual Leave"), "Annual")
	assert.equal(shortLeaveName("Medical Leave"), "Medical")
	assert.equal(shortLeaveName("Annual"), "Annual")
	assert.equal(shortLeaveName("Leave Without Pay"), "Leave Without Pay")
})

test("the balances line reads 'Annual 6 · Medical 13' from the remaining balance", () => {
	const line = balancesLine([
		{ leave_type: "Annual Leave", balance: 6, total: 14 },
		{ leave_type: "Medical Leave", balance: 13.0, total: 14 },
	])
	assert.equal(line, "Annual 6 · Medical 13")
})

test("the balances line keeps a half day and is empty with no leave", () => {
	assert.equal(balancesLine([{ leave_type: "Annual Leave", balance: 12.5 }]), "Annual 12.5")
	assert.equal(balancesLine([]), "")
})

test("the page shows the last five, and no more", () => {
	assert.equal(LAST_ROWS, 5)
	const seven = Array.from({ length: 7 }, (_, i) => ({ name: `R${i}` }))
	assert.deepEqual(
		lastRequests(seven).map((r) => r.name),
		["R0", "R1", "R2", "R3", "R4"],
		"the first five of an already newest-first list"
	)
	assert.equal(lastRequests([{ name: "A" }]).length, 1)
	assert.equal(lastRequests(undefined).length, 0)
})

test("?tab=answered opens See all straight onto the answered list", () => {
	assert.equal(opensOnAnswered({ tab: "answered" }), true)
	assert.equal(opensOnAnswered({}), false)
	assert.equal(opensOnAnswered(undefined), false)
	assert.equal(opensOnAnswered({ tab: "mine" }), false)
})

// ---------------------------------------------------------------- the page

test("order on the page: New request, balances, then your requests", () => {
	const view = noComments(template(read("../../views/Requests.vue")))
	const button = view.indexOf("__('New request')")
	const balances = view.indexOf("<RequestBalances")
	const panel = view.indexOf("<RequestPanel")
	assert.ok(button > -1 && balances > -1 && panel > -1)
	assert.ok(button < balances, "New request is first")
	assert.ok(balances < panel, "balances before the list")
})

test("balances are one line, not cards", () => {
	const src = read("../../components/RequestBalances.vue")
	assert.doesNotMatch(src, /GBalanceCard/, "the two cards are gone")
	assert.match(src, /balancesLine\(shownLeave\.value\)/, "the line is built from the pinned pair")
	assert.match(src, /__\("All balances"\)/, "with the door to every balance")
	assert.match(src, /const PINNED = \[\/annual\|privilege\|earned\/i, \/medical\|sick\/i\]/)
})

test("needs attention is hidden when there is nothing to say", () => {
	const src = noComments(template(read("../../components/RequestBalances.vue")))
	const at = src.indexOf('__("Needs attention")')
	assert.ok(at > -1, "the eyebrow exists")
	const block = src.slice(src.lastIndexOf("<template", at), at)
	assert.match(block, /v-if="rows\.length"/, "and renders only with at least one row")
	assert.match(src, /class="g-eyebrow/)
})

test("the page lists the last five and offers See all", () => {
	const src = read("../../components/RequestPanel.vue")
	assert.match(src, /lastRequests\(myRequests\.value\)/, "your own, newest first, capped")
	assert.match(template(src), /__\("See all"\)/)
	assert.match(template(src), /compact/, "one line each")
})

test("chips and tabs are absent on the page and present in See all", () => {
	const tpl = noComments(template(read("../../components/RequestPanel.vue")))
	const sheet = tpl.indexOf("<GModal")
	assert.ok(sheet > -1, "See all is a sheet")
	const page = tpl.slice(0, sheet)
	const all = tpl.slice(sheet)
	assert.doesNotMatch(page, /g-chips|GSegmented/, "no chips or tabs on the page")
	assert.match(all, /class="g-chips"/, "chips live in See all")
	assert.match(all, /<GSegmented/, "so do the tabs")
	assert.match(all, /g-list-more/, "and the paging")
})

test("tab=answered still reaches the answered list", () => {
	const src = read("../../components/RequestPanel.vue")
	assert.match(src, /opensOnAnswered\(route\.query\)/)
	assert.match(src, /activeTab\.value = "answered"/)
	assert.match(src, /allOpen\.value = true/)
	// The Requests tab stays mounted, so a SECOND visit with ?tab=answered
	// must be heard too: read at setup only, "Answered by you" was a dead tap.
	assert.match(src, /watch\(\s*\(\) => route\.query\.tab/)
	// Approvals still sends people here with that query.
	assert.match(read("../../views/Approvals.vue"), /query: \{ tab: "answered" \}/)
})
