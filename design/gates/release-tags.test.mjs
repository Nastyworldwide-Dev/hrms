// Every released version has a tag (owner, 26 Sep 2026: "i keep looking at
// missing tag release"). The changelog is the list of releases; each entry from
// alpha.2 on must have a `v<version>` tag, or say in its own text that it
// shipped inside another build ("Shipped in 2.0.0-alpha.10"). alpha.1 predates
// tagging (CHANGELOG header).
//   node --test design/gates/release-tags.test.mjs
import { test } from "node:test"
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"

const root = new URL("../../", import.meta.url)
const log = readFileSync(new URL("docs/glass/CHANGELOG.md", root), "utf8")
const tags = new Set(
	execFileSync("git", ["tag", "-l", "v2.0.0*"], { cwd: root, encoding: "utf8" }).split("\n").filter(Boolean)
)

//: [{ version, body }] per changelog entry, newest first.
function entries(text) {
	const parts = text.split(/^## \[/m).slice(1)
	return parts.map((p) => ({ version: p.slice(0, p.indexOf("]")), body: p }))
}

export function untagged(text, tagSet) {
	return entries(text)
		.filter((e) => e.version !== "2.0.0-alpha.1")
		.filter((e) => !tagSet.has(`v${e.version}`) && !/Shipped in 2\.0\.0-/.test(e.body))
		.map((e) => e.version)
}

test("every changelog version has its tag, or says which build carried it", () => {
	assert.deepEqual(untagged(log, tags), [])
})

test("the rule itself: an entry with neither a tag nor a note is caught", () => {
	const sample = "## [2.0.0-alpha.9] — x\n\nText.\n\n## [2.0.0-alpha.8] — x\n\nShipped in 2.0.0-alpha.10.\n"
	assert.deepEqual(untagged(sample, new Set()), ["2.0.0-alpha.9"])
})
