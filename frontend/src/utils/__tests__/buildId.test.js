// A build's own identity, worked out inside the service worker from what it
// precaches (28 Sep 2026: "the new update popup keeps appearing"). The worker
// is served at one fixed URL (/hrms/sw.js) since alpha.12, so the URL can no
// longer tell two builds apart.
import assert from "node:assert/strict"
import { test } from "node:test"

import { buildIdOf } from "../buildId.js"

const manifest = (...entries) => entries.map(([url, revision]) => ({ url, revision }))

test("the same build has the same id", () => {
	const a = manifest(["assets/index-abc.js", null], ["index.html", "r1"])
	const b = manifest(["assets/index-abc.js", null], ["index.html", "r1"])
	assert.equal(buildIdOf(a), buildIdOf(b))
})

test("a changed file is a new build", () => {
	const a = manifest(["assets/index-abc.js", null], ["index.html", "r1"])
	const b = manifest(["assets/index-abc.js", null], ["index.html", "r2"])
	assert.notEqual(buildIdOf(a), buildIdOf(b))
})

test("a renamed chunk is a new build", () => {
	assert.notEqual(
		buildIdOf(manifest(["assets/index-abc.js", null])),
		buildIdOf(manifest(["assets/index-def.js", null]))
	)
})

test("order does not matter", () => {
	const a = manifest(["a.js", "1"], ["b.js", "2"])
	const b = manifest(["b.js", "2"], ["a.js", "1"])
	assert.equal(buildIdOf(a), buildIdOf(b))
})

test("plain strings count too", () => {
	assert.notEqual(buildIdOf(["a.js"]), buildIdOf(["b.js"]))
})

test("nothing precached has no id", () => {
	assert.equal(buildIdOf([]), null)
	assert.equal(buildIdOf(undefined), null)
})
