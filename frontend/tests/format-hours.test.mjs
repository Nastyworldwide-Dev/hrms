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
function loadFormatHours() {
	const source = read("../src/utils/formatters.js")
	const node = parse(source, { ecmaVersion: "latest", sourceType: "module" }).body.find(
		(n) => n.declaration?.declarations?.[0]?.id.name === "formatHours"
	)
	assert.ok(node, "formatters.js exports formatHours")
	const context = vm.createContext({})
	vm.runInContext(source.slice(node.declaration.start, node.declaration.end), context)
	return vm.runInContext("formatHours", context)
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

// Every place an hours Float reaches the screen goes through the formatter.
const sites = {
	"../src/components/OTRequestItem.vue": [/formatHours\(props\.doc\.claimed_hours\)/],
	"../src/components/ReplacementLeaveClaimItem.vue": [/formatHours\(props\.doc\.hours_cost\)/],
	"../src/components/ReplacementLeaveCard.vue": [/formatHours\(bank\.data\?\.hours_available\)/],
	"../src/views/ot/ReplacementLeave.vue": [
		/formatHours\(bank\.data\.hours_available\)/,
		/formatHours\(bank\.data\.hours_claimed\)/,
		/formatHours\(request\.claimed_hours\)/,
		/formatHours\(claimRow\.hours_cost\)/,
	],
	"../src/views/ot/OTRequestForm.vue": [
		/formatHours\(otSummary\.data\.punch_ot_hours\)/,
		/formatHours\(d\.hours\)/,
		/formatHours\(cap\)/,
	],
	"../src/views/ot/ReplacementLeaveClaimForm.vue": [
		/formatHours\(data\.hours_available\)/,
		/formatHours\(cost\)/,
		/formatHours\(available\)/,
	],
	"../src/views/attendance/Dashboard.vue": [/formatHours\(claimableOt\.data\.claimable_hours\)/],
}

test("every hours render goes through formatHours", () => {
	for (const [path, patterns] of Object.entries(sites)) {
		const source = read(path)
		assert.match(source, /import \{[^}]*formatHours[^}]*\} from "@\/utils\/formatters"/, path)
		for (const pattern of patterns) assert.match(source, pattern, path)
	}
})

test("the request sheet formats Float hours fields", () => {
	const source = read("../src/components/RequestActionSheet.vue")
	assert.match(source, /import \{[^}]*formatHours[^}]*\} from "@\/utils\/formatters"/)
	assert.match(source, /formatHours\(raw\)/)
})
