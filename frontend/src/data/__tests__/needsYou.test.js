// The approver queue's resource (revamp slice B3).
//
// One resource, three decisions, each with a failure that only shows up on
// somebody else's phone: whose queue it caches, when it fetches, and which
// endpoint it points at.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const source = readFileSync(join(HERE, "../needsYou.js"), "utf8")

const code = source
	.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
	.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

test("the queue is cached per person", () => {
	// These rows are what is routed to THIS approver. A shared key would serve
	// one approver's queue to the next person who signs in on the same device —
	// routine on a shared factory phone, and it would show them the existence
	// of requests that are none of their business.
	assert.match(code, /personalCacheKey\(/)
})

test("it does not fetch on import", () => {
	// A module-level auto-fetch runs on every screen that imports it, including
	// the login screen, where it 403s and logs noise before anybody is signed in.
	assert.match(code, /auto: false/)
})

test("it points at the unified endpoint", () => {
	// Pointing at the old single-type count is exactly the regression this
	// slice removes, and it would look completely normal — one row, plausible
	// number, six types missing.
	assert.match(code, /url: "hrms\.api\.needs_you\.get_needs_you"/)
	assert.doesNotMatch(code, /get_pending_count/, "that is the remote check-in badge, not this")
})

test("it exports one resource", () => {
	// Two would be two answers to "what is waiting on me", which is the shape
	// the block had before this slice.
	const exports = [...code.matchAll(/export const (\w+)/g)].map((m) => m[1])
	assert.deepEqual(exports, ["needsYouResource"])
})
