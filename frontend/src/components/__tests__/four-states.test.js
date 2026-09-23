// Four states per block (owner ruling D6): loading, empty, error, content.
//
// Each of these blocks used to say something false in one of the four:
// "No shift today" when today's read FAILED, "Nothing waiting on you." when
// the queue could not be read, "Nothing here yet" and "No leave allocated
// yet" while the request was still in flight, and a blank space where the
// expense summary would land. Loading gets a skeleton; failure gets a plain
// line saying we could not load — never an empty message.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
// Comments stripped, so a note ABOUT the old copy cannot satisfy the test.
const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "")
		.replace(/(^|[^:])\/\/[^\n]*/g, "$1")
const template = (src) => src.slice(src.indexOf("<template>"), src.lastIndexOf("</template>"))

test("NowBar: a failed read says so, not 'No shift today'", () => {
	const src = code(read("../NowBar.vue"))
	assert.match(src, /__\("We couldn't load today\. Pull down to try again\."\)/)
	// the error check comes BEFORE the no-label fallback in the state line
	const line = src.slice(src.indexOf("const stateLine"))
	assert.ok(
		line.indexOf("nowResource.error") > -1 &&
			line.indexOf("nowResource.error") < line.indexOf('"No shift today"'),
		"error is decided before the empty fallback"
	)
	assert.match(template(src), /<GSkeleton/, "loading draws a skeleton")
})

test("NeedsYou: a failed read is not 'Nothing waiting on you.'", () => {
	const src = template(code(read("../NeedsYou.vue")))
	const error = src.indexOf("needsYouResource.error")
	const empty = src.indexOf('"Nothing waiting on you."')
	assert.ok(error > -1 && error < empty, "the error branch precedes the empty line")
	assert.match(src, /<GListPanel[^>]*\bloading\b/, "loading draws skeleton rows")
})

test("Requests 'Your last 5' passes its resource, so loading and failure are not 'Nothing here yet'", () => {
	const panel = template(code(read("../RequestPanel.vue")))
	assert.match(panel, /<RequestList\s+:items="lastFive"[^>]*:resource="lastFiveResource"/)
	const list = template(code(read("../RequestList.vue")))
	const skeleton = list.indexOf("<GSkeleton")
	assert.ok(skeleton > -1, "RequestList has a loading skeleton")
	assert.ok(skeleton < list.indexOf("<GEmptyState"), "skeleton is decided before the empty state")
})

test("LeaveBalance: skeleton while loading, not 'No leave allocated yet'", () => {
	const src = template(code(read("../LeaveBalance.vue")))
	const loading = src.search(/<GBalanceGrid[^>]*\sloading\b/)
	assert.ok(loading > -1, "loading GBalanceGrid exists")
	assert.ok(loading < src.indexOf("No leave allocated yet"), "loading is decided before empty")
})

test("ExpenseClaimSummary: skeleton while loading, not a blank", () => {
	const src = template(code(read("../ExpenseClaimSummary.vue")))
	assert.match(src, /<GSkeleton/)
})
