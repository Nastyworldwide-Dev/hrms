// The router had NO catch-all, so any unknown URL rendered a completely blank
// page — no message, no way back, indistinguishable from a crash. The 8.x audit
// found it via /design, which is import.meta.env.DEV only and therefore absent
// from production builds: a route the app legitimately does not have, presenting
// as a fatal error.
//
// This asserts the route TABLE rather than mounting the app, so it needs no DOM
// and no session. Run with: node --test "frontend/**/*.test.js"
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { createRouter, createMemoryHistory } from "vue-router"

const source = readFileSync(fileURLToPath(new URL("../index.js", import.meta.url)), "utf8")

test("a catch-all route exists and is registered LAST", () => {
	assert.match(source, /pathMatch\(\.\*\)\*/, "the router must define a catch-all")
	const catchAll = source.indexOf("pathMatch(.*)*")
	const devOnly = source.indexOf("import.meta.env.DEV")
	assert.ok(
		devOnly === -1 || catchAll > devOnly,
		"the catch-all must be pushed after the dev-only /design route, or it swallows it in dev"
	)
})

test("an unknown path resolves to NotFound rather than nothing", () => {
	// A minimal table with the same catch-all shape, to prove the pattern
	// matches what it needs to — vue-router is the thing under test here.
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/home", name: "Home", component: {} },
			{ path: "/:pathMatch(.*)*", name: "NotFound", component: {} },
		],
	})

	assert.equal(router.resolve("/home").name, "Home")
	assert.equal(router.resolve("/design").name, "NotFound", "a production-absent route")
	assert.equal(router.resolve("/nonsense/deep/path").name, "NotFound")
	assert.equal(router.resolve("/").name, "NotFound", "even the bare root must land somewhere")
})

test("the NotFound view it points at exists", () => {
	assert.match(source, /views\/NotFound\.vue/)
	assert.doesNotThrow(() =>
		readFileSync(fileURLToPath(new URL("../../views/NotFound.vue", import.meta.url)))
	)
})
