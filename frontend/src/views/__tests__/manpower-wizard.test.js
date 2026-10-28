// Manpower Request wizard, alpha.68 slice M1: source-level pins like manpower-hr-board.test.js; the
// rules themselves are tested in utils/__tests__/manpowerRequest.test.js. Expected words are the
// slice brief's (.claude/plans/alpha68/mp-screens.md, M1), not read back from the file.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(
	fileURLToPath(new URL("../manpower/ManpowerRequestWizard.vue", import.meta.url)),
	"utf8"
)
const tpl = src.slice(0, src.indexOf("<script setup>"))

test("no segmented control is left; every short fixed list is a tick-list", () => {
	assert.doesNotMatch(src, /GSegmented/)
	for (const list of ["EMPLOYMENT_TYPES", "REQUEST_TYPES", "BANDS", "soonKeys"])
		assert.match(tpl, new RegExp(`v-for="[^"]*in ${list}"`), `${list} is drawn as rows`)
	assert.match(tpl, /bandMeaning|:sublabel="__\(b\.meaning\)"/, "each band row says what it is")
})

test("empty slots say Choose…, never Required or Optional inside the field", () => {
	assert.match(src, /__\(['"]Choose…['"]\)/)
	assert.doesNotMatch(tpl, /placeholder="[^"]*(Required|Optional)/)
	assert.match(tpl, /__\(['"]Place, and why['"]\)/)
})

test("one title for the type card and a title for the request kind", () => {
	assert.match(tpl, /__\("What is this for\?"\)/)
})

test("the footers that repeated their rows are gone", () => {
	for (const gone of [
		"It cannot be changed",
		"Monthly, in RM",
		"Leave the start date empty",
		"Pick one. Nadi sets the urgency",
	])
		assert.doesNotMatch(src, new RegExp(gone))
})

test("money shows RM and thousands; over budget is a warning banner", () => {
	assert.match(src, /moneyText\(/)
	assert.match(src, /parseMoney\(/)
	assert.doesNotMatch(tpl, /\(RM\)/)
	assert.match(tpl, /<GBanner[^>]*variant="warning"/)
})

test("the urgency chip is neutral, not the error colour", () => {
	assert.doesNotMatch(src, /URGENCY_CHIP/)
	assert.doesNotMatch(tpl, /status="rejected"/)
})

test("blocked Next points at its one reason", () => {
	assert.match(tpl, /:aria-describedby="blocker \? 'mp-reason' : undefined"/)
	assert.match(tpl, /id="mp-reason"/)
})

test("leaving: Cancel on step 1, Back later; the step name is shown once", () => {
	assert.match(tpl, /step === 0 \? __\(["']Cancel["']\) : __\(["']Back["']\)/)
	assert.equal(
		(tpl.match(/__\(STEPS\[step\]\.title\)/g) || []).length,
		2,
		"title + scroller label only"
	)
})

test("the replacement list gets a search over 8 people", () => {
	assert.match(tpl, /<GSearchBar/)
	assert.match(src, /> 8/)
})

test("review greys a blank optional answer as Optional, left blank, edit links get a chevron", () => {
	assert.match(src, /__\("Optional, left blank"\)/)
	assert.doesNotMatch(src, /Not answered|Not given/)
	assert.match(tpl, /<ChevronRight/)
})

test("'If other' questions are filtered, not always drawn", () => {
	assert.match(src, /visibleQuestions\(/)
})

test("final pass: money shows raw text while focused, formats on blur", () => {
	assert.match(tpl, /@focusin=/)
	assert.match(tpl, /@focusout=/)
	assert.match(src, /moneyShown\(/)
})

test("final pass: radio rows rove, arrow keys move between them", () => {
	assert.match(src, /rovingNext\(/)
	assert.match(src, /tabStop\(/)
	assert.equal((tpl.match(/@keydown="\s*radioKey\(/g) || []).length, 5, "five radio groups")
	assert.equal((tpl.match(/:tabindex="tabStop\(/g) || []).length, 5)
})

test("final pass: the progress bar stops moving for reduced motion", () => {
	assert.match(
		src,
		/@media \(prefers-reduced-motion: reduce\)\s*{[^}]*\.mp-fill[^}]*transition: none/
	)
})

test("final pass: wording from the audit", () => {
	assert.match(tpl, /:placeholder="__\('Not fixed'\)"/)
})

test("final pass: the person picker resets with the department and keeps the chosen row", () => {
	assert.match(src, /staffQuery\.value = ""/)
	assert.match(src, /p\.name === model\.replacing_employee/)
})
