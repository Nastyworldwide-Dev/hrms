// Owner, 2 Nov 2026: "why does Nadi on desktop or laptop not have More" —
// everyone on a laptop saw Help, SOPs, Announcements, Public holidays and
// Approva, and nothing else. Organizational Chart, TruTrip, Approvals, Roster
// and Manpower requests were added to the phone's More screen only, because
// More.vue built its "Your team" list inline and the side nav had no copy.
// Fix: one list (data/teamNav.js) that both read, and the travel links too.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const nav = read("components/SideNav.vue")
const more = read("views/More.vue")

test("the side nav and More read one 'Your team' list", () => {
	assert.match(nav, /from "@\/data\/teamNav"/, "the side nav imports the shared team list")
	assert.match(more, /from "@\/data\/teamNav"/, "and More reads the same one")
	assert.match(nav, /useTeamItems\(__\)/)
	assert.match(more, /useTeamItems\(__\)/)
})

test("neither keeps its own copy of a team row", () => {
	for (const [file, src] of [
		["SideNav.vue", nav],
		["More.vue", more],
	]) {
		assert.doesNotMatch(
			src,
			/title: __\("(Team|Roster|Approvals|Organizational Chart|Manpower requests)"\)/,
			file
		)
	}
})

test("the side nav renders the team rows with their counts", () => {
	const template = nav.slice(0, nav.indexOf("<script"))
	assert.match(template, /v-for="item in teamItems"/)
	assert.match(template, /item\.badge/)
})

test("the side nav offers the travel links More offers", () => {
	assert.match(nav, /EXTERNAL_LINKS/)
	assert.match(nav, /openExternal\(/)
	const template = nav.slice(0, nav.indexOf("<script"))
	assert.match(template, /v-for="item in externalItems"/)
})
