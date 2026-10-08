// The grouped Approvals page, as the owner approved it (23 Sep 2026):
// YOURS (Other teams was removed on 8 Oct 2026); department, then kind; one line per person;
// five lines then "See all"; "Show more (N left)" in twenties; never an
// endless list (NN/g infinite scrolling; Baymard load-more).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Approvals.vue", import.meta.url)), "utf8")
const template = page.slice(0, page.indexOf("<script"))

test("the page is grouped by the shared module, not a flat list", () => {
	assert.match(page, /groupApprovals\(visibleRows\.value\)/)
	assert.doesNotMatch(template, /v-for="row in rows"/)
})

test("one section, in plain words: Other teams is gone (owner ruling 8 Oct 2026)", () => {
	// 23 Sep asked for two sections; 8 Oct: "the page lists only requests sent to the approver"
	assert.match(template, /__\("Yours"\)/)
	assert.doesNotMatch(template.replace(/<!--[\s\S]*?-->/g, ""), /__\("Other teams"\)/)
	assert.doesNotMatch(template, /'s team"/)
})

test("a group shows five, then See all; expanded pages in twenties with what is left", () => {
	assert.match(page, /pageOf\(/)
	assert.match(page, /__\("See all"\)/)
	assert.match(page, /__\("Show more \(\{0\} left\)"/)
})

test("one line per person; tapping it lists that person's requests, each opening the sheet", () => {
	assert.match(template, /personLine\(person, __\)/)
	assert.match(template, /@click="openPerson\(person\)"/)
	assert.match(template, /v-for="row in person\.rows"|v-for="row in personOpen\.rows"/)
})

test("nothing is folded: with Other teams gone there is no collapsed section", () => {
	// 8 Oct 2026: startCollapsed belonged to Other teams
	assert.doesNotMatch(page, /startCollapsed/)
})

test("Home counts only check-ins sent to you (Yours), from the same server answer", () => {
	const needs = readFileSync(fileURLToPath(new URL("../../components/NeedsYou.vue", import.meta.url)), "utf8")
	assert.match(needs, /needsYouResource\.data\?\.checkins/)
})
