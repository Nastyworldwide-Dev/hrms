// alpha.8 r3 (owner, 25 Sep 2026: "jumpy jumpy stuff … every bit measured").
// Measured frame by frame in WebKit at 402×874, cold and warm cache: every
// jump on 36 screens was a placeholder whose size differed from the answer
// that replaced it, or a block that arrived late. `e2e/scroll-and-shift-audit.mjs`
// is the proof (0 of 36 both passes); these pin each cause at its source.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const css = read("../../theme/glass-components.css")

test("an overlay Ionic has not hydrated yet takes no place in the page", () => {
	// Undefined <ion-modal> is a plain block; a flex column paid its gap —
	// Home's Today card +12, the Calendar's rows +24 for one frame.
	assert.match(css, /:is\(ion-modal, ion-popover[^)]*\):not\(\.ios\):not\(\.md\)\s*\{\s*display: none;/)
})

test("an empty queue is the same row as its skeleton, not a loose line", () => {
	for (const [file, words] of [
		["../NeedsYou.vue", "Nothing waiting on you."],
		["../../views/Approvals.vue", "Nothing is waiting on you."],
	]) {
		const src = read(file)
		assert.match(src, new RegExp(`<GListRow :label='__\\("${words.replace(".", "\\.")}"\\)'`), file)
		assert.doesNotMatch(src, /class="g-empty-line/, `${file}: no loose empty line`)
	}
	assert.match(read("../../views/Approvals.vue"), /loading :rows="1"/)
})

test("a skeleton row is the icon row's height: the skeleton sits in the real well", () => {
	assert.match(read("../glass/GListPanel.vue"), /<span class="g-row__well">\s*<GSkeleton width="29px"/)
})

test("a cached answer is not swapped for a skeleton on refresh", () => {
	assert.match(read("../NeedsYou.vue"), /needsYouResource\.loading && !needsYouResource\.data/)
	assert.match(read("../../views/Approvals.vue"), /waiting\.loading && !waiting\.data/)
	assert.match(read("../../views/Approvals.vue"), /cache: personalCacheKey\("nsty:approvals-waiting"\)/)
})

test("the Today card holds the button's and the lines' places while loading", () => {
	const panel = read("../CheckInPanel.vue")
	assert.match(panel, /v-else-if="!settings\.data && settings\.loading"\s*class="g-today__action-skeleton"\s*height="48px"/)
	assert.match(css, /\.g-today #open-checkin-modal,\s*\.g-today \.g-today__action-skeleton \{\s*margin-top: 4px;/)
	// A unitless line-height token is not a length: min-height needs size × ratio.
	assert.match(css, /\.g-now__row \{[^}]*min-height: calc\(var\(--g-type-panel-title-size\) \* var\(--g-type-panel-title-line-height\)\)/)
	assert.match(css, /\.g-now__detail \{[^}]*min-height: calc\(var\(--g-type-caption-size\) \* var\(--g-type-caption-line-height\)\)/)
	assert.match(read("../NowBar.vue"), /v-else-if="pending" class="g-now__detail"/)
})

test("You draws Manager and Shift rows from the first frame", () => {
	const src = read("../../views/Profile.vue")
	assert.doesNotMatch(src, /v-if="managerName" class="g-form-row/)
	assert.doesNotMatch(src, /v-if="shiftName" class="g-form-row/)
	assert.match(src, /managerName \|\| __\("None"\)/)
})

test("the overtime form paints once, with its days line", () => {
	assert.match(read("../../views/ot/OTRequestForm.vue"), /v-if="formFields\.data && \(props\.id \|\| daysAnswered\)"/)
})

test("the quiet board is the skeleton's shape: one form row", () => {
	const src = read("../Announcements.vue")
	assert.doesNotMatch(src, /<GListPanel loading :rows="2" \/>/)
	assert.match(src, /<div class="g-form-row"><GSkeleton/)
})
