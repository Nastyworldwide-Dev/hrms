// The calendar's two reads (revamp §4, slices C2/C3).
//
// The split is the design: `monthFlags` is the small per-date payload a 44px
// tile can draw, `daySheet` is the sentences, fetched only when somebody taps.
// Collapsing them into one read would make a month view load every punch,
// every leave application and every roster line for thirty days at once.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const code = readFileSync(join(HERE, "../calendar.js"), "utf8")
	.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

function resource(name) {
	const start = code.indexOf(`export const ${name} = createResource(`)
	assert.ok(start >= 0, `${name} is exported`)
	const end = code.indexOf("export ", start + 10)
	return code.slice(start, end === -1 ? undefined : end)
}

test("the month and the day are two separate reads", () => {
	// One read would pull a month of punches to draw thirty dots.
	assert.equal((code.match(/createResource\(/g) || []).length, 2)
	assert.match(resource("monthFlags"), /get_month_flags/)
	assert.match(resource("daySheet"), /get_day/)
})

test("the month's dots are cached per person", () => {
	// Flags are audience-filtered (the event dot uses the announcement fence)
	// and employee-specific. A shared key would draw one person's month for
	// the next person on the device.
	assert.match(resource("monthFlags"), /personalCacheKey\(/)
})

test("the day sheet is not cached", () => {
	// It is per DATE and per persona, and a cache keyed on the resource rather
	// than the date would serve yesterday's sheet for today.
	assert.doesNotMatch(resource("daySheet"), /cache:/)
})

test("neither fetches on import", () => {
	for (const name of ["monthFlags", "daySheet"]) {
		assert.match(resource(name), /auto: false/, `${name} waits to be asked`)
	}
})

test("both endpoints are in the calendar module", () => {
	const urls = [...code.matchAll(/url: "([^"]+)"/g)].map((m) => m[1])
	assert.equal(urls.length, 2)
	for (const url of urls) assert.match(url, /^hrms\.api\.calendar\./)
})
