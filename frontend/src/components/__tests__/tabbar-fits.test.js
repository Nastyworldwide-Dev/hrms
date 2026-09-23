// FIVE LABELS HAVE TO FIT ONE BAR.
//
// Deployed 23 September 2026 reading "CALENDARREQUESTS" on every screen in the
// app. Cause: the tab label was moved onto the modular type ramp's 12px bottom
// step the day before (slice A2) and nothing checked that five uppercase words
// still fit a 390px bar beside a 20px icon. They did not, and each label's
// `overflow: hidden` clipped its OWN box while the boxes themselves overlapped
// — so the clipping made it look deliberate.
//
// This is the check that was missing. It is arithmetic rather than a render,
// because the failure is arithmetic: the widest label at the chosen size
// against the slot the bar can give it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const tokens = JSON.parse(readFileSync(join(SRC, "../../design/tokens.json"), "utf8"))

const code = (text) =>
	text
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

//: The narrowest supported viewport (§27) — if it fits here it fits everywhere.
const FLOOR = parseFloat(tokens.layout["viewport-floor"].value)
const GUTTER = parseFloat(tokens.spacing["screen-gutter"].value)

//: Inter Tight uppercase, measured from the deployed screenshot rather than
//: assumed: "CALENDAR" rendered 65.7 CSS px at 12px — 0.684em per character
//: INCLUDING its tracking. Conservative for a fitting check, because the real
//: font may be wider on a device that substitutes.
const EM_PER_CHAR = 0.684

//: Horizontal padding ion-tab-button gives each label. Two labels that touch
//: are unreadable even when neither is clipped, so the check demands a real
//: gap rather than mere non-overlap.
const MIN_GAP = 6

function labelWidth(word, sizePx, trackingEm) {
	// The measurement above already carries 0.07em of tracking; scale the rest.
	const perChar = sizePx * (EM_PER_CHAR - 0.07 + trackingEm)
	return word.length * perChar
}

test("five tab labels fit the narrowest supported bar", () => {
	const step = tokens.type.scale["tab-label"]
	const size = parseFloat(step.size)
	const tracking = parseFloat(step.tracking)
	const items = code(read("data/navItems.js"))

	// The bar's own labels, read from the shared list rather than retyped —
	// a test with its own copy would pass while the bar overflowed.
	const shortTitles = [...items.matchAll(/shortTitle: "([^"]+)"/g)].map((m) => m[1])
	assert.ok(shortTitles.length >= 5, "the nav list has labels")

	const tabSource = items.slice(items.indexOf("export const TAB_ITEMS"))
	const indices = [...tabSource.matchAll(/NAV_ITEMS\[(\d+)\]/g)].map((m) => Number(m[1]))
	const barLabels = [...indices.map((i) => shortTitles[i]), "More"]
	assert.equal(barLabels.length, 5, "five destinations")

	const slot = (FLOOR - 2 * GUTTER) / 5
	const failures = []
	for (const label of barLabels) {
		const width = labelWidth(label.toUpperCase(), size, tracking)
		if (width + MIN_GAP > slot) {
			failures.push(
				`${label.toUpperCase()} needs ${width.toFixed(1)}px in a ${slot.toFixed(1)}px slot`
			)
		}
	}
	assert.deepEqual(
		failures,
		[],
		`at ${size}px/${tracking}em the bar overflows at ${FLOOR}px — this is what shipped as "CALENDARREQUESTS"`
	)
})

test("the 12px ramp step is proven to be the thing that broke it", () => {
	// A regression test has to fail on the code that caused the defect. At
	// 12px with the ramp's tracking the longest label does NOT fit, which is
	// exactly what the deploy showed.
	const slot = (FLOOR - 2 * GUTTER) / 5
	const broken = labelWidth("CALENDAR", 12, 0.07)
	assert.ok(broken + MIN_GAP > slot, "12px must not fit, or this test proves nothing")
})

test("the tab label says it is outside the ramp, and why", () => {
	// A value that disagrees with the system needs its reason next to it, or
	// the next person moves it back onto the ramp for tidiness.
	const step = tokens.type.scale["tab-label"]
	assert.match(step.description, /not a step on the|outside it/i)
	assert.match(step.description, /fit|bar/i, "and names the constraint that wins")
})

test("the label never wraps, and is still allowed to ellipsis", () => {
	// Belt and braces: the arithmetic above governs the chosen size, and these
	// keep a long translation from stacking two lines into a 64px bar.
	const css = code(read("theme/glass-components.css"))
	const block = css.slice(
		css.indexOf(".g-tabbar__label {"),
		css.indexOf(".g-tabbar__label--active")
	)
	assert.match(block, /white-space: nowrap/)
	assert.match(block, /text-overflow: ellipsis/)
})

test("the bar does not grow with the reader's text size", () => {
	// FOUND BY ARITHMETIC, 23 September 2026, an hour after fixing the
	// collision: type was converted to rem the day before (WCAG 1.4.4), so at
	// 120% text a rem-sized tab label overflows its slot and
	// "CALENDARREQUESTS" comes straight back — for exactly the people who
	// raised their text size because they were struggling to read it.
	//
	// 1.4.4 governs CONTENT. It does not ask a navigation label with an icon
	// above it to scale past its own container: the destinations stay
	// reachable and named at every setting, which is what the criterion is
	// protecting.
	const emitted = readFileSync(join(SRC, "theme/glass.css"), "utf8")
	const size = /--g-type-tab-label-size:\s*([^;]+);/.exec(emitted)
	assert.ok(size, "the tab label size is emitted")
	assert.match(size[1].trim(), /px$/, "it stays in CSS px")

	// And everything a person READS still scales — the exemption is one role,
	// not a retreat from the criterion.
	const caption = /--g-type-caption-size:\s*([^;]+);/.exec(emitted)
	assert.match(caption[1].trim(), /rem$/, "body-ish type still answers to the reader")
})

test("the exemption is one named role, not a habit", () => {
	// A list that grows is a list that eventually contains everything.
	const builder = readFileSync(join(SRC, "../../design/build-tokens.mjs"), "utf8")
	const set = /const FIXED_PX_ROLES = new Set\(\[([^\]]*)\]\)/.exec(builder)
	assert.ok(set, "the exempt roles are a named set")
	const roles = [...set[1].matchAll(/"([^"]+)"/g)].map((m) => m[1])
	assert.deepEqual(roles, ["tab-label"], "exactly one role is exempt")
})
