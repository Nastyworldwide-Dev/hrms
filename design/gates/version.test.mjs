// One version, one source of truth (audit F-2 / APP-26; SemVer 2.0.0,
// Keep a Changelog 1.1). The PWA had "0.0.0" in package.json and showed only
// a build timestamp, so "which version are you on?" had no answer. The
// version lives in frontend/package.json, is stamped into the bundle, is
// shown on You, and must have a changelog entry.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const root = new URL("../../", import.meta.url)
const read = (path) => readFileSync(new URL(path, root), "utf8")
const version = JSON.parse(read("frontend/package.json")).version

//: SemVer 2.0.0 section 9: a pre-release is -<dot-separated identifiers>.
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$/

test("the PWA has a real semantic version", () => {
	assert.match(version, SEMVER)
	assert.notEqual(version, "0.0.0")
})

test("the changelog's newest entry is this version", () => {
	const log = read("docs/glass/CHANGELOG.md")
	const newest = log.match(/^## \[([^\]]+)\]/m)
	assert.ok(newest, "the changelog has a version heading")
	assert.equal(newest[1], version)
})

test("the build stamps the version into the bundle", () => {
	assert.match(read("frontend/vite.config.js"), /__APP_VERSION__:\s*JSON\.stringify\(/)
})

test("You shows the version, not only a build time", () => {
	assert.match(read("frontend/src/views/Profile.vue"), /__APP_VERSION__/)
})
