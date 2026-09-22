// The toast wrapper's contract, checkable under bun (revamp slice A7).
//
// Its BEHAVIOUR — which variant announces assertively, what text reaches the
// live region, that the visible toast still happens — is tested in
// tests/toast-announces.test.mjs, which needs mock.module to stand in for
// frappe-ui (its index re-exports through directory specifiers, which ESM
// cannot resolve). bun has not implemented mock.module, and the pre-commit
// hook runs mapped tests under bun, so that file cannot live here.
//
// What CAN be checked in both runners is the contract this module exists to
// hold: that a toast is never shown without also being spoken. That is the
// invariant a future edit would break by adding a second `toast(` call or by
// dropping the announce, and neither needs the module to be importable.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = fileURLToPath(new URL(".", import.meta.url))
const read = (p) => readFileSync(join(HERE, p), "utf8")

const code = (text) =>
	text
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const wrapper = code(read("../toast.js"))

test("nothing is shown without also being spoken", () => {
	// One announce for one toast. A second `toast(` added later without an
	// announce is a message that reaches sighted users only.
	assert.equal((wrapper.match(/\btoast\(/g) || []).length, 1, "exactly one toast call")
	assert.equal((wrapper.match(/\bannounce\(/g) || []).length, 1, "and exactly one announcement")
	assert.ok(
		wrapper.indexOf("announce(") < wrapper.indexOf("return toast("),
		"announced before the toast is queued, so the region is populated either way"
	)
})

test("severity carries to the announcement", () => {
	// "Could not check you in" must interrupt; "Saved" must not. If this maps
	// the wrong way round, a screen-reader user is interrupted by every save
	// and told about failures only when the reader happens to reach them.
	assert.match(wrapper, /variant === "error" \? "assertive" : "polite"/)
})

test("both lines are announced, joined into one sentence", () => {
	// The title says what happened and the text says what to do. Hearing only
	// the first is being told a problem with no way out of it.
	assert.match(wrapper, /\[title, text\]\.filter\(Boolean\)\.join\(". "\)/)
})

test("the announcer is imported with its extension", () => {
	// Vite resolves an extensionless sibling; the node test runner does not.
	// This module is imported by a test that runs outside Vite.
	assert.match(wrapper, /from "\.\/announce\.js"/)
})
