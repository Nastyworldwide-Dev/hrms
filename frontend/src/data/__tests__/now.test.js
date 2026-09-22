// The Home status resource (revamp §2, slice D1).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const code = readFileSync(join(HERE, "../now.js"), "utf8")
	.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

test("it is one call", () => {
	// Home already makes several, and the top of the first screen is the worst
	// place to add a fourth spinner.
	assert.equal((code.match(/createResource\(/g) || []).length, 1)
	assert.match(code, /url: "hrms\.api\.now\.get_now"/)
})

test("it is cached per person", () => {
	// A shift window and an open session are one employee's facts. A shared
	// key would put somebody else's shift at the top of your Home.
	assert.match(code, /personalCacheKey\(/)
})

test("it does not fetch on import", () => {
	// The bar fetches when it mounts. A module-level fetch would run on the
	// login screen and 403 before anybody is signed in.
	assert.match(code, /auto: false/)
})
