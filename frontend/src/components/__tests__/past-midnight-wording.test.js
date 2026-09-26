// A check-out after midnight is said plainly (owner, 26 Sep 2026: "special
// wording so it's clear it was cleared out"): on its work day "· next day" and
// one footer line; on the clock date "Counted on Thu 25 Sep"; on Team
// "OUT 01:41 (next day)" or "Worked past midnight · counted on …".
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the day sheet names the next-day tap and where a stray one counted", () => {
	const sheet = read("../DaySheet.vue")
	assert.match(sheet, /punch\.next_day \? `\$\{label\} · \$\{__\("next day"\)\}`/)
	assert.match(sheet, /__\("Worked past midnight: the check-out after 12 am counts on this day\."\)/)
	assert.match(sheet, /__\('Counted on \{0\}'/)
})

test("the team line says (next day) and where it counted", () => {
	const team = read("../../views/team/TeamDashboard.vue")
	assert.match(team, /member\.out_next_day \? __\("\{0\} \(next day\)", \[out\]\)/)
	assert.match(team, /__\("Worked past midnight · counted on \{0\}"/)
})
