// The standing numbers, in one call (revamp slice C1).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const code = readFileSync(join(HERE, "../requestsSummary.js"), "utf8")
	.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

test("the figures are cached per person", () => {
	// Every one of them is about the session user's own record. A shared key
	// would show one employee's leave balance to the next person on the device.
	assert.match(code, /personalCacheKey\(/)
})

test("it does not fetch on import", () => {
	assert.match(code, /auto: false/)
})

test("it is one call, not four", () => {
	// The screen would otherwise wait on four endpoints in series before it
	// could draw anything.
	assert.equal((code.match(/createResource\(/g) || []).length, 1)
	assert.match(code, /url: "hrms\.api\.requests_summary\.get_requests_summary"/)
})
