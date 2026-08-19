import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) =>
	readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

// The production incident this pins (2026-08-19): frappe-ui fires
// `auto: true` resources SYNCHRONOUSLY inside createResource, so a resource
// declared at module scope fetches while the import graph is still
// evaluating. With setConfig("resourceFetcher") living in main.js's BODY,
// those fetches fell back to the bare request — no /api/method/ prefix —
// and GET https://<site>/hrms.api.team.has_team answered 404 for every
// fresh session: the Team page and Team tabs vanished site-wide while
// stale-cached sessions noticed nothing. The config must therefore be a
// side-effect module evaluated before anything that can declare a resource.

test("resourceConfig sets the fetcher at module scope", () => {
	const source = read("../src/resourceConfig.js")
	assert.match(
		source,
		/setConfig\("resourceFetcher", makeLoudRequest\(frappeRequest\)\)/
	)
})

test("main.js imports resourceConfig before anything else", () => {
	const source = read("../src/main.js")
	const firstImport = source.match(/^import .*$/m)[0]
	assert.equal(
		firstImport,
		'import "./resourceConfig"',
		"the config import must be main.js's FIRST import — later, and " +
			"module-scope auto resources race it and fetch unprefixed"
	)
})

test("main.js body no longer sets the fetcher late", () => {
	const source = read("../src/main.js")
	assert.doesNotMatch(source, /setConfig\("resourceFetcher"/)
})
