// The grid carries dots; the day sheet carries words (revamp §4).
//
// The owner asked for a calendar where "each date must serve function — what
// is going on in that date" — without the screen overflowing with text. That
// is not an editorial problem, it is a structural one: a tile is about 44px,
// which is the tap-target floor it cannot go under, and 44px holds a date and
// up to three 4px dots and nothing else.
//
// So the split is the design. Anything that puts a sentence back on a tile,
// or that lets the dot count grow, breaks the thing that makes the month
// legible — and neither would look wrong in a diff.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const api = readFileSync(join(SRC, "../../hrms/api/calendar.py"), "utf8").replace(
	/(^|\n)(\s*)#[^\n]*/g,
	(m, nl, indent) => nl + indent
)

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const calendar = code(read("components/glass/GCalendar.vue"))
const sheet = code(read("components/DaySheet.vue"))
const css = code(read("theme/glass-components.css"))

test("a tile draws marks, never words", () => {
	const tile = calendar.slice(calendar.indexOf('v-for="d in days"'), calendar.indexOf("</button>"))
	assert.match(tile, /g-cal__dot/, "the flags are dots")
	// The only text in a tile is the date itself.
	const interpolations = [...tile.matchAll(/\{\{([^}]+)\}\}/g)].map((m) => m[1].trim())
	assert.deepEqual(interpolations, ["d.day"], "nothing but the date is written on a tile")
})

test("the dot cap is enforced server-side, so the wire and the tile agree", () => {
	// Capping on the screen would mean the payload promises more than the tile
	// draws, and the difference would be invisible until somebody counted.
	assert.match(api, /MAX_DOTS = 3/)
	assert.match(api, /if len\(entry\) < MAX_DOTS/)
	assert.doesNotMatch(calendar, /slice\(0, 3\)/, "the component does not re-cap")
})

test("a dot is never the only signal", () => {
	// §14.1. A dot is colour and nothing else, so the flags go into the tile's
	// accessible name — a screen reader that heard "14 September, present" and
	// then three unnamed marks would be worse off than with no dots at all.
	assert.match(calendar, /const FLAG_LABELS = \{/)
	assert.match(calendar, /:aria-label="dayLabel\(d\)"/)
	const label = calendar.slice(calendar.indexOf("function dayLabel"))
	assert.match(label, /d\.flags\.map/, "every flag is spoken")
	const dots = calendar.slice(calendar.indexOf('v-if="d.flags?.length"'))
	assert.match(dots, /aria-hidden="true"/, "and the marks themselves are not read twice")
})

test("the dots sit under the numeral, not beside it", () => {
	// A date can be two digits. Dots beside it would reflow the row between
	// the 9th and the 10th.
	const block = css.slice(css.indexOf(".g-cal__dots"), css.indexOf(".g-cal__dot {"))
	assert.match(block, /position: absolute/)
	assert.match(block, /bottom: 4px/)
	const tile = css.slice(css.indexOf("\n.g-cal__day {"), css.indexOf("\n.g-cal__day--"))
	assert.match(tile, /position: relative/, "so the dots anchor to the tile itself")
})

test("every flag has a colour of its own", () => {
	const flags = ["leave", "holiday", "event", "needs_you"]
	for (const flag of flags) {
		assert.match(css, new RegExp(`\\.g-cal__dot--${flag}`), `${flag} is drawn`)
	}
	// And they come from tokens: a raw hex here is a colour that will not
	// follow the theme.
	const dots = css.slice(css.indexOf(".g-cal__dot {"), css.length)
	const block = dots.slice(0, dots.indexOf("\n}\n", dots.indexOf("needs_you")))
	assert.doesNotMatch(block, /#[0-9a-f]{3,6}/i, "dot colours are tokens")
})

test("the day sheet holds no role logic", () => {
	// Persona is the SERVER's answer (revamp P5/KR2): the team line shows only
	// when the server sent a coverage section.
	assert.doesNotMatch(sheet, /HR Manager|HR User|isApprover|hasHRRole|roles/, "no role check")
	assert.match(sheet, /daySheet\.data\?\.coverage/, "it renders what arrived")
	assert.match(sheet, /v-if="teamSummary"/, "and nothing when a section did not")
})

test("the team is ONE line that opens the Team page on that date (ruling 1)", () => {
	// The line is the door, the Team page is the room: no names, no tile
	// strip here (AUDIT-PLAN "Team line", no repeat).
	assert.match(sheet, /teamLine\(coverage\.value, props\.date/)
	assert.match(sheet, /name: "TeamView", query: \{ date: props\.date \}/)
	assert.doesNotMatch(sheet, /GMetaGrid|Who is off/)
})

test("a manager never sees why somebody is off", () => {
	// Owner's ruling, 22 Sep 2026: type yes, reason never.
	//
	// Asserted as BEHAVIOUR, not as prose. The first version of this looked for
	// the rule in a comment — in a file this test strips comments from — which
	// is a check that can only ever fail or pass for the wrong reason. What
	// matters is that the field is never selected and never rendered.
	const who = api.slice(api.indexOf("def _who_is_off"), api.indexOf("def _coverage"))
	assert.doesNotMatch(who, /"description"/, "the reason is never selected")
	assert.match(who, /"leave_type": row\.leave_type/, "the type is")
	assert.doesNotMatch(sheet, /description/, "and the screen has nothing to render")
})

test("the month's dots follow the month being looked at", () => {
	// Fetched once on mount, stepping to October would draw September's dots
	// under October's dates — the same defect the per-month attendance
	// resources in this component were built to prevent.
	const component = code(read("components/AttendanceCalendar.vue"))
	assert.match(component, /watch\(\s*firstOfMonth/, "the flags follow the month")
	assert.match(component, /monthFlags\.fetch\(\{/)
})

test("tapping a tile opens the day", () => {
	const component = code(read("components/AttendanceCalendar.vue"))
	assert.match(component, /@select="openDay"/)
	assert.match(component, /<DaySheet/)
	// Dismissal comes from the framework's own event: the sheet can be closed
	// by a swipe or a backdrop tap as well as a button, and a parent listening
	// only to a button is left with `open` stuck true.
	assert.match(sheet, /@did-dismiss="\$emit\('close'\)"/)
})
