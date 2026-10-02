// Team roster "Assign" (30 Sep 2026). The sheet's button rendered as an empty
// lime pill: GButton draws its text from the `label` prop and has no default
// slot, so the words written between its tags were thrown away (owner's
// screenshot). And a Shift Supervisor rosters their own shifts too, so their
// own row reads "You".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const view = read("../TeamRoster.vue")
const button = read("../../../components/glass/GButton.vue")

test("GButton takes its text from label, not a default slot", () => {
	assert.match(button, /pending \? pendingLabel \|\| label : label/)
	assert.doesNotMatch(button, /<slot\s*\/>/, "no default slot to put words in")
})

test("the Assign shift button has words", () => {
	const tag = view.slice(view.indexOf("<GButton"), view.indexOf("/>", view.indexOf("<GButton")))
	assert.match(tag, /:label="__\('Assign shift'\)"/)
})

test("a supervisor's own row reads You", () => {
	assert.match(view, /member\.is_self \? __\("You"\) : member\.employee_name/)
})

// 2 Oct 2026: a supervisor changes and removes their team's shifts from Nadi.
const data = read("../../../data/team.js")

test("each day in the strip is a button that opens that day", () => {
	assert.match(view, /<button[\s\S]*?v-for="day in weekDays"[\s\S]*?@click="openDay\(member, day\)"/)
})

test("the day sheet has Change and Remove, wired to the roster endpoints", () => {
	assert.match(view, /:label="__\('Change shift'\)"/)
	assert.match(view, /:label="__\('Remove this day'\)"/)
	assert.match(data, /url: "hrms\.api\.roster\.change_shift_day"/)
	assert.match(data, /url: "hrms\.api\.roster\.remove_shift_day"/)
})
