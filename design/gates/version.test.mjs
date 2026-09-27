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

// alpha.14 (owner, 27 Sep 2026): "version update with version release name
// properly. no date and time displayed in app." R12: professional words, no
// themed names. The release name says what the release delivers; it lives
// next to the version in package.json (one source), heads the changelog
// entry, titles the GitHub Release, and is what You shows beside the number.
// Named from 2.0.0-alpha.14; the ones already shipped keep their number only.
const releaseName = JSON.parse(read("frontend/package.json")).releaseName
const named = !/^2\.0\.0-alpha\.([0-9]|1[0-3])$/.test(version)

test("the release has a plain, descriptive name", { skip: !named && "released before names" }, () => {
	assert.equal(typeof releaseName, "string")
	assert.match(releaseName, /^[A-Z][A-Za-z,&' -]{3,60}$/)
})

test("the changelog heading carries it", { skip: !named && "released before names" }, () => {
	const newest = read("docs/glass/CHANGELOG.md").match(/^## \[([^\]]+)\] — ([^\n]+)$/m)
	assert.equal(newest[1], version)
	assert.match(newest[2], new RegExp(`^${releaseName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} — \\d{4}-\\d{2}-\\d{2}$`))
})

test("You shows the version and its name, and no date or time", async () => {
	const profile = read("frontend/src/views/Profile.vue")
	assert.match(profile, /__APP_RELEASE_NAME__/)
	assert.doesNotMatch(profile, /__APP_BUILD__|buildString/)
	// the build stamp is for diagnostics reports only; no screen imports it
	const { execSync } = await import("node:child_process")
	const onScreen = execSync("grep -rl __APP_BUILD__ frontend/src --include=*.vue || true", { cwd: new URL(".", root) }).toString().trim()
	assert.equal(onScreen, "")
})

test("the GitHub Release is titled with the name", () => {
	assert.match(read("scripts/release.sh"), /--title "Nadi \$version — \$name"/)
})
