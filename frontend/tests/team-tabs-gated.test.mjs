// Class guard: a "Team …" tab must never be shown unconditionally.
//
// The recurring bug — a hardcoded TAB_BUTTONS array with a "Team X" entry —
// gave every plain employee a permanently empty (or inappropriate) Team tab.
// RequestPanel fixed it by gating on isApprover; the leave / expense / shift
// list views each shipped the same hardcoded array with no gate. This scans
// every view for a TAB_BUTTONS that names a Team tab and fails if that file
// doesn't reference isApprover — so the next hardcoded team tab fails the build
// instead of leaking to a non-manager.

import assert from "node:assert/strict"
import { readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { test } from "node:test"

const VIEWS = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src")

function walk(dir) {
	const out = []
	for (const e of readdirSync(dir, { withFileTypes: true })) {
		const p = path.join(dir, e.name)
		if (e.isDirectory()) out.push(...walk(p))
		else if (e.name.endsWith(".vue")) out.push(p)
	}
	return out
}

test("every view with a Team tab gates it on isApprover", () => {
	const offenders = []
	for (const file of walk(VIEWS)) {
		const src = readFileSync(file, "utf8")
		// a TAB_BUTTONS (or tabButtons) declaration that names a "Team …" tab
		const declaresTeamTab = /TAB_BUTTONS[\s\S]{0,200}?["']Team /.test(src)
		if (declaresTeamTab && !src.includes("isApprover")) {
			offenders.push(path.relative(VIEWS, file))
		}
	}
	assert.deepEqual(
		offenders,
		[],
		`these views show a Team tab without an isApprover gate: ${offenders.join(", ")}`
	)
})
