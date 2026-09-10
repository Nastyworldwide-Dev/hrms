// navItems.js imports Vue icon components, so it cannot be loaded under
// node:test — which is the reason appLinks.js is kept free of Vue imports and
// carries the role logic. This file therefore pins navItems.js as SOURCE, the
// way index.html is pinned in theme-boot.test.js.
//
// What is worth pinning: navItems must not grow a second opinion about who
// sees an app row. The allowlist lives in appLinks.js and `visibleAppItems`
// exists only to attach icons to whatever that returns. A role name appearing
// in this file would mean two lists to keep in step, and the one that drifts
// is always the one without the test.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../navItems.js", import.meta.url), "utf8")

test("visibleAppItems delegates to the allowlist instead of filtering itself", () => {
	assert.match(source, /visibleAppLinks/, "navItems must call visibleAppLinks")
	assert.match(
		source,
		/export const visibleAppItems\s*=\s*\(userRoles\)\s*=>\s*\n?\s*visibleAppLinks\(userRoles\)/,
		"visibleAppItems must be a thin map over visibleAppLinks"
	)
})

test("navItems declares no role names of its own", () => {
	// The allowlist is appLinks.js's job. Catching a stray role string here is
	// cheaper than discovering the two lists disagree in production.
	for (const role of [
		"Accounts Manager",
		"Accounts User",
		"System Manager",
		"HR Manager",
		"HR User",
		"Projects User",
		"Projects Manager",
	]) {
		assert.ok(!source.includes(role), `navItems.js should not name the role "${role}"`)
	}
})

test("every app key has an icon, so a gated row never renders blank", () => {
	// visibleAppItems attaches APP_ICONS[key]; a key with no icon would pass
	// the allowlist and then render an empty slot.
	const block = source.match(/const APP_ICONS = \{([\s\S]*?)\}/)
	assert.ok(block, "APP_ICONS block not found")
	const keys = [...block[1].matchAll(/(\w+): markRaw\(/g)].map((m) => m[1])
	assert.deepEqual(keys.sort(), ["approva", "board"])
})
