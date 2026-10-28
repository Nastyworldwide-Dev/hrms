// HR's manpower monitoring in Nadi (S4, 22 Oct 2026). Source-level pins, like the other tests in this
// directory; the REAL screens are proved in a browser (.claude/tmp/manpower-s4/). Rulings:
// .claude/plans/manpower-plan.md ("HR monitoring in Nadi = HR Issue Board pattern"), mockup tab 6.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const board = read("../manpower/ManpowerHRBoard.vue")
const detail = read("../manpower/ManpowerRequestDetail.vue")
const more = read("../More.vue")
const template = (src) => src.slice(0, src.indexOf("<script"))

test("the board is one stat panel of four tiles, with the owner's four short words", () => {
	assert.match(board, /<GStatPanel[^>]*:columns="4"/)
	assert.equal(
		(template(board).match(/<GStatTile/g) || []).length,
		1,
		"tiles are drawn by one v-for"
	)
	for (const word of ["With manager", "Needs HR", "Recruiting", "Filled"])
		assert.match(board, new RegExp(`__\\("${word}"\\)`))
})

test("the board carries the HR eyebrow, a search, a department filter and 5-then-See-all lists", () => {
	assert.match(board, /__\("HR · People & Culture"\)/)
	assert.match(board, /<GSearchBar/)
	assert.match(board, /<GSelect/)
	assert.match(board, /groupRows\(/)
	assert.match(board, /__\(["']See all/)
})

test("the board has loading, error and empty states and reads the server's board", () => {
	assert.match(board, /hrms\.api\.manpower\.hr_board/)
	assert.match(board, /<ResourceError/)
	assert.match(board, /<GEmptyState/)
	assert.match(board, /loading/)
})

test("the over-30-days state is a word and a shape, not only a colour", () => {
	assert.match(board, /needsHrState\(/)
	assert.match(board, /<AlertTriangle|<TriangleAlert|<CircleAlert/)
})

test("a tapped row opens the EXISTING detail page", () => {
	assert.match(board, /name: "ManpowerRequestDetailView"/)
	assert.match(board, /params: \{ id:/)
})

test("the board uses theme tokens, never a literal colour", () => {
	assert.doesNotMatch(board, /#[0-9a-fA-F]{3,8}\b/)
	assert.doesNotMatch(board, /\brgba?\(/)
})

test("More offers 'Manpower requests' to HR only, with a count of what needs HR", () => {
	assert.match(more, /__\("Manpower requests"\)/)
	assert.match(more, /userResource\.data/)
	assert.match(more, /hasHRRole/)
	assert.match(more, /needs_hr/)
	assert.match(more, /boardRoute/)
})

test("the detail page has a Hiring section for HR, saved through set_hiring_status", () => {
	assert.match(detail, /hrms\.api\.manpower\.set_hiring_status/)
	assert.match(detail, /hiringSection\(/)
	assert.match(detail, /hiringProblems\(/)
	assert.match(detail, /HIRING_CHOICES/)
	assert.match(detail, /<GListPanel/)
	assert.match(detail, /<GTextarea/)
})

test("every state that dims Save has one visible reason the button points at", () => {
	assert.match(detail, /id="mp-hiring-why"/)
	assert.match(detail, /aria-describedby/)
	assert.match(detail, /mp-hiring-why/)
	assert.match(detail, /:disabled="/)
})

test("while the manager has not decided, the Hiring controls cannot be used", () => {
	assert.match(detail, /inert/)
})
