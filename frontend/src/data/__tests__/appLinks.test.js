// WHETHER an app row is offered is the server's answer (audit F-15: no role
// names in the frontend). The role rule and its tests live in
// hrms/api/app_links.py + test_app_links.py; here, the PWA shows exactly the
// keys the server offered, and nothing on a bad payload.
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

import { APP_LINKS, visibleAppLinks } from "../appLinks.js"

test("the rows shown are exactly the keys the server offered", () => {
	assert.deepEqual(
		visibleAppLinks(["board"]).map((l) => l.key),
		["board"]
	)
	assert.deepEqual(
		visibleAppLinks(["approva", "board"]).map((l) => l.key),
		["approva", "board"]
	)
	assert.deepEqual(visibleAppLinks([]), [])
})

test("an unknown key offers nothing (the PWA only links what it knows)", () => {
	assert.deepEqual(visibleAppLinks(["somewhere-else"]), [])
})

test("a missing or malformed payload renders no rows, never throws", () => {
	// myApps.data is undefined on first paint.
	for (const bad of [undefined, null, "board", {}, 0]) {
		assert.deepEqual(visibleAppLinks(bad), [])
	}
})

test("no role names in the frontend's app list", () => {
	const source = readFileSync(new URL("../appLinks.js", import.meta.url), "utf8")
	for (const role of ["Accounts User", "HR Manager", "Projects User", "System Manager"]) {
		assert.ok(!source.includes(`"${role}"`), `appLinks.js must not name the role "${role}"`)
	}
	for (const link of APP_LINKS) assert.equal(link.roles, undefined)
})
