// Owner, 15 Oct 2026: an Attendance Report Viewer (Mia, Shenzhen) opens Team and
// sees her whole company, view only. Team shows for her; Roster never does.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

test("More shows Team for a company viewer but keeps Roster behind hasTeam", () => {
	const more = read("views/More.vue")
	assert.match(more, /\.\.\.\(hasTeam\.data \|\| hasCompanyView\.data\s*\?\s*\[\{ key: "team"/)
	const at = more.indexOf('key: "roster"')
	const roster = more.slice(more.lastIndexOf("...(", at), at)
	assert.match(roster, /\.\.\.\(hasTeam\.data\s*\?/)
	assert.doesNotMatch(roster, /hasCompanyView/)
})

test("the side nav offers Team to a company viewer", () => {
	assert.match(
		read("components/SideNav.vue"),
		/hasTeam\.data \|\| hasCompanyView\.data\s*\?\s*\[\{ icon: markRaw\(Users\), title: __\("Team"\)/
	)
})

test("the dashboard hides the roster link and says view only in company view", () => {
	const view = read("views/team/TeamDashboard.vue")
	assert.match(
		view,
		/v-if="teamStatus\.data\?\.members\?\.length && !teamStatus\.data\?\.company_view"\s*:to="\{ name: 'TeamRosterView' \}"/
	)
	assert.match(view, /You see everyone in your company, view only\./)
})

test("the gate is the server's has_company_view", () => {
	assert.match(read("data/team.js"), /url: "hrms\.api\.team\.has_company_view"/)
})
