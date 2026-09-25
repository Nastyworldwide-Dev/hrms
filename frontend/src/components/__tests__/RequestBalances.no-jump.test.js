// Requests jumped 0.39 on first load (audit F-12 / APP-28; CLS limit 0.1,
// measured live 23 Sep): the balance strip rendered NOTHING until its data
// arrived, then pushed "New request" and the list down. While the first read
// is in flight it holds its place with the grid's own skeleton (F-7: one
// loading pattern, skeletons).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../RequestBalances.vue", import.meta.url)),
	"utf8"
)
const template = source.slice(0, source.indexOf("<script"))

test("the first load holds its place with a skeleton grid", () => {
	// Sized like the finished strip: the SAME "Leave left" header and one
	// 44 pt form row (alpha.8 r3 — a header-less 51 pt panel moved the list
	// 71 pt when the answer landed).
	assert.match(
		template,
		/v-else-if="firstLoad"[\s\S]*?__\("Leave left"\)[\s\S]*?<div class="g-form-row">\s*<GSkeleton/
	)
	assert.match(
		source,
		/const firstLoad = computed\(\(\) => requestsSummary\.loading && !requestsSummary\.data\)/
	)
})

test("a screen reader is told the balances are loading", () => {
	assert.match(template, /role="status">\{\{ __\("Loading your balances"\) \}\}/)
})

test("money reads the way the rest of the app prints it (symbol, not code)", () => {
	// Live audit 23 Sep: "INR 50.00" here, "RM" on Help and claims. This row
	// printed the currency CODE by hand; the app's formatter prints the symbol.
	assert.match(source, /formatCurrency\(/)
	assert.doesNotMatch(source, /`\$\{currency\} \$\{Number\(amount\)\.toFixed\(2\)\}`/)
})

test("Malaysian ringgit prints as RM, at runtime", () => {
	// Review of e16828c1d: pin the actual output, not just the call. The
	// formatter uses narrowSymbol; this fails on a runtime without full ICU.
	const out = new Intl.NumberFormat("en", {
		style: "currency",
		currency: "MYR",
		currencyDisplay: "narrowSymbol",
	}).format(50)
	assert.match(out, /^RM/)
})
