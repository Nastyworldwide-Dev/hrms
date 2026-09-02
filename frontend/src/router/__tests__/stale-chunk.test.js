// After a deploy the service worker purges old hashed chunks; a tab still on the
// previous build then fails its next lazy import mid-navigation. Without a guard
// that rejection surfaced as a broken/half-old route with no recovery. onError
// now reloads once into the current build — but ONLY for that specific failure,
// never for an ordinary route/component error, which a blanket reload would turn
// into an infinite refresh. This pins the predicate that draws that line.

import assert from "node:assert/strict"
import { test } from "node:test"

import { isStaleChunkError } from "../stale-chunk.js"

test("recognises the stale-chunk wording of each engine", () => {
	// Chromium, Firefox, and webpack-era bundlers word it these three ways.
	assert.ok(isStaleChunkError("Failed to fetch dynamically imported module: /assets/x-abc123.js"))
	assert.ok(isStaleChunkError("error loading dynamically imported module"))
	assert.ok(isStaleChunkError("Importing a module script failed."))
	assert.ok(isStaleChunkError("ChunkLoadError: Loading chunk 42 failed."))
})

test("does NOT reload for ordinary errors — a blanket reload would loop", () => {
	assert.equal(isStaleChunkError("TypeError: cannot read properties of undefined"), false)
	assert.equal(isStaleChunkError("Navigation cancelled from /a to /b"), false)
	assert.equal(isStaleChunkError(""), false)
	assert.equal(isStaleChunkError(undefined), false)
	assert.equal(isStaleChunkError(null), false)
})
