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
