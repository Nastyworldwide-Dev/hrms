// The grouped Approvals page, as the owner approved it (23 Sep 2026):
// YOURS then OTHER TEAMS; department, then kind; one line per person;
// five lines then "See all"; "Show more (N left)" in twenties; never an
// endless list (NN/g infinite scrolling; Baymard load-more).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Approvals.vue", import.meta.url)), "utf8")
const template = page.slice(0, page.indexOf("<script"))

test("the page is grouped by the shared module, not a flat list", () => {
	assert.match(page, /groupApprovals\(rows\.value\)/)
	assert.doesNotMatch(template, /v-for="row in rows"/)
})

test("two sections, in plain words", () => {
	assert.match(template, /__\("Yours"\)/)
	assert.match(template, /__\("Other teams"\)/)
	assert.match(template, /__\("\{0\}'s team", \[team\.approverName\]\)/)
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

test("Other teams folds shut when it is long", () => {
	assert.match(page, /startCollapsed/)
})

test("Home counts only check-ins sent to you (Yours), from the same server answer", () => {
	const needs = readFileSync(fileURLToPath(new URL("../../components/NeedsYou.vue", import.meta.url)), "utf8")
	assert.match(needs, /needsYouResource\.data\?\.checkins/)
})

test("Other teams is a heading too, with a wired disclosure (heading navigation finds it)", () => {
	assert.match(template, /<h2 class="m-0">\s*<button[\s\S]*aria-controls="approvals-other-teams"/)
	// v-show, not v-if: aria-controls must point at an element that exists
	assert.match(template, /v-show="otherOpen" id="approvals-other-teams"/)
})
