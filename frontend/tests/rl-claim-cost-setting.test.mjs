// The claim form told the employee "0.5 day costs N h" from the HR setting,
// then charged a hardcoded 8 h per day when validating. A site configured
// for 7.5 h/day saw its own cap refuse a claim the server would accept.
// Run: cd frontend && node --test tests/rl-claim-cost-setting.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(
		new URL("../src/views/ot/ReplacementLeaveClaimForm.vue", import.meta.url)
	),
	"utf8"
)

test("hours cost comes from replacement_leave_hours_per_day, not a literal 8", () => {
	const fn = source.slice(source.indexOf("function validateClaimedDays"))
	const body = fn.slice(0, fn.indexOf("\n}\n"))
	assert.doesNotMatch(body, /numeric \* 8\b/)
	const costLine = body.split("\n").find((line) => /const cost =/.test(line))
	assert.ok(costLine, "cost is computed in validateClaimedDays")
	assert.match(costLine, /replacement_leave_hours_per_day/)
	assert.match(costLine, /\?\? 8/)
})
