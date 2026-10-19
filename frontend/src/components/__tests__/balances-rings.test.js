// All balances as rings (owner pick B, 19 Oct 2026: "need a better visual info
// rather than simple linear text"). Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const src = read("../RequestBalances.vue")
const template = src.slice(0, src.indexOf("<script"))
const sheet = template.slice(template.indexOf("<GModal"), template.indexOf("</GModal>"))
const api = read("../../../../hrms/api/requests_summary.py")
const css = read("../../theme/glass-components.css")

test("the sheet is a ring per leave type, not a list of text rows", () => {
	assert.match(sheet, /v-for="row in rankedLeave"/)
	assert.match(sheet, /class="g-leave-ring"/)
	assert.doesNotMatch(sheet, /<GListRow/, "the text list is gone")
})

test("each ring draws left and taken from the one helper", () => {
	assert.match(sheet, /ringArcs\(row, RING_C\)\.left/)
	assert.match(sheet, /ringArcs\(row, RING_C\)\.taken/)
})

test("each ring is one sentence to VoiceOver; the drawing is hidden", () => {
	assert.match(sheet, /role="group"\s+:aria-label="ringLabel\(row\)"/)
	assert.match(sheet, /class="g-leave-ring__dial" aria-hidden="true"/)
	const fn = src.slice(src.indexOf("function ringLabel"))
	assert.match(fn, /balanceLine\(row\)/, "same words as before: '6 of 14 left' or the expiry")
})

test("an expiry still beats everything else under the ring", () => {
	assert.match(
		sheet,
		/v-if="row\.expiring_soon"[\s\S]*?Expires \{0\}[\s\S]*?v-else-if="row\.taken > 0"/
	)
})

test("the server sends what was taken, from the ledger", () => {
	assert.match(api, /"taken": flt\(entry\.get\("leaves_taken"\)\)/)
	assert.match(api, /"allocated": allocated/)
	const map = read("../../../../hrms/api/__init__.py")
	assert.match(map, /"leaves_taken": flt\(details\.get\("leaves_taken"\), precision\)/)
})

test("the leave ring does not share GProgressRing's class", () => {
	// .g-ring is the KPI ring (88px, flex: none); reusing the name squeezed
	// every balance cell to 88px and restyled the KPI dial (design review).
	assert.doesNotMatch(sheet, /class="g-ring[ _"]/)
	const kpi = css.indexOf(".g-ring {")
	assert.equal(css.indexOf(".g-ring {", kpi + 1), -1, "one .g-ring rule, GProgressRing's")
})

test("left reads in light mode: accent ink, not lime on a light track", () => {
	assert.match(css, /\.g-leave-ring__left\s*\{\s*stroke: var\(--g-accent-ink\);/)
})

test("rings are Glass tokens only, two across, an odd last ring spans", () => {
	const block = css.slice(
		css.indexOf(".g-leave-ring-legend {"),
		css.indexOf(".g-leave-ring__sub--warn")
	)
	assert.doesNotMatch(block, /#[0-9a-f]{3,6}\b/i, "no hard-coded colour")
	assert.match(
		css,
		/\.g-leave-rings\s*\{[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/
	)
	assert.match(css, /\.g-leave-ring:last-child:nth-child\(odd\)\s*\{\s*grid-column: 1 \/ -1;/)
})
