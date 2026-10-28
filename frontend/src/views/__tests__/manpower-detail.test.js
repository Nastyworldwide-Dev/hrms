import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

const src = readFileSync(new URL("../manpower/ManpowerRequestDetail.vue", import.meta.url), "utf8")

test("title block: position + 'Manpower request · name'", () => {
	assert.match(src, /<h1[^>]*>\s*\{\{ doc\.position_title \}\}/)
	assert.match(src, /Manpower request · \{0\}/)
})
test("one fact per row: Job type and Reason for hire, no 'This is'", () => {
	assert.match(src, /__\("Job type"\)/)
	assert.match(src, /__\("Reason for hire"\)/)
	assert.doesNotMatch(src, /__\("This is"\)/)
	assert.doesNotMatch(src, /detailKind/)
})
test("closed reason is a second line under the status", () => {
	assert.match(src, /where\.reason/)
})
test("band shown with bandLabel()", () => {
	assert.match(src, /bandLabel\(d\.band\)/)
})
test("tracker says 'Not yet' for pending steps, manager name on the second line", () => {
	assert.match(src, /__\("Not yet"\)/)
	assert.match(src, /\$\{who\}/)
})
test("All answers shows its count", () => {
	assert.match(src, /All answers \(\{0\}\)/)
})
test("Withdraw is the quiet destructive row, not a danger button", () => {
	assert.match(src, /g-form-row--destructive/)
	assert.doesNotMatch(src, /Withdraw request'\)" danger/)
})
test("withdraw reason placeholder is 'Reason (optional)'", () => {
	assert.match(src, /:placeholder="__\('Reason \(optional\)'\)"/)
	assert.doesNotMatch(src, /For example: the role is covered/)
})
test("Hiring status is a tick-list, Save is full width", () => {
	assert.doesNotMatch(src, /GSegmented/)
	assert.match(src, /role="radiogroup"/)
	assert.match(src, /class="mt-2 w-full"/)
})
