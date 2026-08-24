// The regression guard for this pass's crash class.
//
// Four of the five live crashes fixed alongside this file were the same
// defect: an identifier used but never imported. `router.push()` in
// data/employees.js with no router import (session expiry threw
// ReferenceError instead of redirecting to login), `__()` in
// utils/commonUtils.js and in both shift forms' validateDates(),
// `frappeRequest` in main.js. None of them are reachable by a unit test of
// the module — importing the module does not execute the branch, and the
// branch only runs on a failure path in a browser.
//
// What DOES catch every one of them, at every call site, forever, is
// ESLint's no-undef — which had never run in this project: .eslintrc.js was
// CommonJS in a "type": "module" package, so Node refused to load it, and
// two plugins the config extends were never installed. A per-module test
// asserting "the import statement is present" would be a tautology; this
// asserts the property that actually matters, across the whole tree.
//
// Run with: yarn --cwd frontend test
import { test } from "node:test"
import assert from "node:assert/strict"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), "..")

// Rules that encode "this would throw at runtime" or "this is dead weight".
// Formatting is deliberately excluded — prettier/prettier is noisy and says
// nothing about correctness.
const CORRECTNESS_RULES = [
	"no-undef",
	"no-unused-vars",
	"no-async-promise-executor",
	"vue/require-v-for-key",
	"vue/valid-v-for",
	"vue/no-mutating-props",
	"vue/require-valid-default-prop",
	"vue/return-in-computed-property",
]

test("no source file references an undefined identifier", async () => {
	const { ESLint } = await import("eslint")
	const eslint = new ESLint({ cwd: FRONTEND })
	const results = await eslint.lintFiles(["src"])

	const offences = []
	for (const r of results) {
		for (const m of r.messages) {
			if (!CORRECTNESS_RULES.includes(m.ruleId)) continue
			offences.push(
				`${r.filePath.replace(FRONTEND + "/", "")}:${m.line} ${m.ruleId} — ${m.message}`
			)
		}
	}

	assert.deepEqual(
		offences,
		[],
		`ESLint correctness rules must stay clean:\n${offences.join("\n")}`
	)
})
