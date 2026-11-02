// alpha.14 O (27 Sep 2026 sweep): a leader's things lived in two homes —
// Approvals under You, Team under More, Roster only inside Team. You is the
// person; what a leader does for others is one group on More, "Your team":
// Approvals, Team, Roster, each shown only when the server says it applies.
// The Approvals count was check-ins only (get_pending_count), so four leave
// requests waiting showed no number; it is now everything waiting on you,
// the same source Home's Needs you reads.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const more = read("../More.vue")
const you = read("../Profile.vue")
// the rows themselves: one list, shared with the laptop SideNav (2 Nov 2026)
const team = read("../../data/teamNav.js")

test("You is only you: no Approvals row there", () => {
	assert.doesNotMatch(you, /name: "Approvals"/)
})

test("More has one 'Your team' group with Approvals, Team and Roster, each server-gated", () => {
	assert.match(more, /\{\{ __\("Your team"\) \}\}/)
	assert.match(more, /useTeamItems\(__\)/)
	const block = team.slice(team.indexOf("return computed"))
	assert.match(block, /isApprover\.data/)
	assert.match(block, /hasTeam\.data/)
	assert.match(block, /name: "Approvals"/)
	assert.match(block, /route: "\/team"/)
	assert.match(block, /route: "\/team\/roster"/)
})

test("the Approvals count is everything waiting on you", () => {
	assert.match(team, /needsYouResource\.data\?\.total/)
	assert.match(team, /needsYouResource\.data\?\.checkins/)
	assert.doesNotMatch(team, /pendingCountResource/)
})
