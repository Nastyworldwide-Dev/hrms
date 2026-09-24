// Hours are stored as Float and computed from punches, so a raw render showed
// "5.669444444h overtime" in the PWA. formatHours is the one display rule:
// at most 2 decimals, trailing zeros dropped, empty reads as "0".
// Run: cd frontend && node --test tests/format-hours.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"

const require = createRequire(import.meta.url)
const { parse } = require("acorn")
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")

// formatters.js imports frappe-ui and an @/ alias, which node cannot load, so the
// declaration itself is lifted out and run — the real source, not a copy.
function loadFormatHours(name = "formatHours") {
	const source = read("../src/utils/formatters.js")
	const node = parse(source, {
		ecmaVersion: "latest",
		sourceType: "module",
	}).body.find((n) => n.declaration?.declarations?.[0]?.id.name === name)
	assert.ok(node, `formatters.js exports ${name}`)
	const context = vm.createContext({})
	vm.runInContext(
		source.slice(node.declaration.start, node.declaration.end),
		context
	)
	return vm.runInContext(name, context)
}

test("formatHours: at most two decimals, trailing zeros dropped, empty is 0", () => {
	const formatHours = loadFormatHours()
	assert.equal(formatHours(5.669444), "5.67")
	assert.equal(formatHours(5.669444444), "5.67")
	assert.equal(formatHours(3), "3")
	assert.equal(formatHours(2.5), "2.5")
	assert.equal(formatHours(2.5), "2.5")
	assert.equal(formatHours(null), "0")
	assert.equal(formatHours(undefined), "0")
	assert.equal(formatHours("1.10"), "1.1")
})

// A claim cap stored as 5.669444444 must never display as 5.67: typing the
// shown number would then be refused by the cap check that compares the full value.
test("formatHoursCap: rounds down to two decimals, exact values survive", () => {
	const formatHoursCap = loadFormatHours("formatHoursCap")
	assert.equal(formatHoursCap(5.669444444), "5.66")
	assert.equal(formatHoursCap(5.67), "5.67")
	assert.equal(formatHoursCap(5.669999999), "5.66") // the tolerance must never round a cap up
	assert.equal(formatHoursCap(0.29), "0.29")
	assert.equal(formatHoursCap(3), "3")
	assert.equal(formatHoursCap(null), "0")
	assert.ok(Number(formatHoursCap(5.669444444)) <= 5.669444444)
})

// Every place an hours Float reaches the screen goes through the formatter.
// Display rows read as time ("12h 30m", ruling C8) through hoursAsTime; the
// OT form keeps decimals because its input field takes a decimal number.
test("display rows render hours as time, not decimals (ruling C8)", () => {
	for (const [path, pattern] of [
		["../src/components/OTRequestItem.vue", /hoursAsTime\(props\.doc\.claimed_hours\)/],
		["../src/components/ReplacementLeaveClaimItem.vue", /hoursAsTime\(props\.doc\.hours_cost\)/],
		["../src/components/RequestBalances.vue", /hoursAsTime\(overtime\.unclaimed_hours\)/],
	]) {
		const source = read(path)
		assert.match(source, pattern, path)
		assert.doesNotMatch(source, /hours\)?\.toFixed\(/, path)
	}
})

const sites = {
	"../src/views/ot/OTRequestForm.vue": [
		// alpha.6 C3: the day list and summary read as time (ruling C8), rounded
		// down to the minute because they are caps.
		/capAsTime\(otSummary\.value\.data\.punch_ot_hours\)/,
		/formatHours: capAsTime/,
		/Math\.floor\(\(Number\(h\) \|\| 0\) \* 60/,
		/formatHoursCap\(cap\)/,
	],
}

test("every hours render goes through formatHours", () => {
	for (const [path, patterns] of Object.entries(sites)) {
		const source = read(path)
		// formatHours or its cap-aware sibling; either way the one display rule.
		assert.match(
			source,
			/import \{[^}]*formatHours(Cap)?[^}]*\} from "@\/utils\/formatters"/,
			path
		)
		for (const pattern of patterns) assert.match(source, pattern, path)
	}
})

test("the request sheet formats Float hours fields", () => {
	const source = read("../src/components/RequestActionSheet.vue")
	assert.match(
		source,
		/import \{[^}]*formatHours[^}]*\} from "@\/utils\/formatters"/
	)
	assert.match(source, /formatHours\(raw\)/)
})
