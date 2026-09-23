// Help, one screen (alpha.5, 23 Sep 2026). The owner's screenshot: four
// filter chips, a "New IT Ticket →" button ABOVE the list, and three lines of
// id / type / "by <you>" on every row. Now: open first (5, then See all),
// finished behind one Closed row, Who to ask, then ONE primary button at the
// bottom. Both sides render the same split (components/HelpSplitList.vue).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { parse } from "@vue/compiler-sfc"

const sfc = (path) => {
	const { template, scriptSetup } = parse(
		readFileSync(new URL(path, import.meta.url), "utf8")
	).descriptor
	return { markup: template.content, script: scriptSetup.content }
}

const split = sfc("../../../components/HelpSplitList.vue")
const hub = sfc("../HelpdeskHub.vue")
const LISTS = { IT: "../HelpdeskList.vue", HR: "../../issues/IssueList.vue" }

test("the split: open first (five, then See all), finished behind one Closed row", () => {
	assert.match(split.script, /splitHelp\(/)
	assert.match(split.script, /\.slice\(0, 5\)/)
	assert.match(split.markup, /__\("Open"\)/)
	assert.match(split.markup, /__\(['"]See all \(\{0\}\)['"]/)
	assert.match(split.markup, /__\(['"]Closed['"]\)/)
	assert.equal((split.markup.match(/<GModal\b/g) || []).length, 2, "all-open and closed sheets")
	assert.match(split.script, /const PAGE = 20/)
	assert.match(split.markup, /__\("Show more"\)/)
	assert.match(split.markup, /<GEmptyState[\s\S]*?__\('Nothing open'\)/)
})

test("rows carry the day and 'Waiting on you' — no id, no 'by', no details", () => {
	assert.match(split.markup, /:sublabel="helpRowMeta\(/)
	assert.match(split.markup, /<GStatusChip/)
	for (const [side, path] of Object.entries(LISTS)) {
		const list = sfc(path)
		assert.match(list.markup, /<HelpSplitList/, `${side} uses the shared split`)
		assert.doesNotMatch(list.script, /\bCHIPS\b|filterTickets|__\("by"\)/, side)
		assert.doesNotMatch(list.markup, /aria-pressed|<GButton|ArrowRight/, `${side}: no chips, no button`)
		assert.doesNotMatch(list.markup + list.script, /issue\.details|ticket\.name,/, side)
	}
})

test("Help: the pills say HR and IT, without counts", () => {
	assert.match(hub.script, /label: __\("HR"\)/)
	assert.match(hub.script, /label: __\("IT"\)/)
	assert.doesNotMatch(hub.script, /withCount|openIssueCount|openTicketCount/)
})

test("Help: lists, then Who to ask, then ONE primary button at the bottom", () => {
	const buttons = hub.markup.match(/<GButton\b/g) || []
	assert.equal(buttons.length, 1, "exactly one primary button")
	assert.match(hub.script, /__\("Report an issue"\)/)
	assert.match(hub.script, /__\("New ticket"\)/)
	assert.doesNotMatch(hub.markup, /#trailing|ArrowRight/, "no arrow icon")
	const lists = hub.markup.indexOf("<HelpdeskList")
	const who = hub.markup.indexOf("whoToAsk")
	const button = hub.markup.indexOf("<GButton")
	assert.ok(lists < who && who < button, "lists → Who to ask → button")
})
