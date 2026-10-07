// The unselected select-mode tick on Approvals is a ring that marks an interactive control, so its
// outline needs 3:1 non-text contrast (WCAG 1.4.11). --g-ink3 measured 2.93:1 on the light page
// (design review of 6fd6ea79b); --g-ink2 is 6.8:1 on white and 7.6:1 in dark.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const view = readFileSync(fileURLToPath(new URL("../Approvals.vue", import.meta.url)), "utf8")

test("the unselected tick's ring uses the strong ink, not the faint one", () => {
	const rule = view.match(/\.g-approvals__tick \{[^}]*\}/)?.[0]
	assert.ok(rule, "the tick rule exists")
	assert.match(rule, /border: 2px solid var\(--g-ink2\)/)
})
