// The transition-integrity invariant is that a routed page (.ion-page.g-page)
// is OPAQUE — Ionic stacks live pages during a transition, and a transparent
// page composites the one below it as a double-exposure (old + new visible
// mid-navigation). That rule once read `background: var(--g-ground)`, a token
// defined NOWHERE, so with no fallback it computed to transparent and silently
// broke the invariant. This pins the fix: the page ground must resolve to a
// DEFINED token, and the undefined --g-ground must not come back.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(
	fileURLToPath(new URL("../glass-components.css", import.meta.url)),
	"utf8"
)
const themeCss = readFileSync(fileURLToPath(new URL("../glass.css", import.meta.url)), "utf8")

test("the page ground uses the defined --g-bg token, not the undefined --g-ground", () => {
	const rule = css.match(/\.ion-page\.g-page\s*\{[^}]*\}/)
	assert.ok(rule, ".ion-page.g-page rule must exist")
	assert.match(rule[0], /background:\s*var\(--g-bg/, "page ground must come from --g-bg")
})

test("--g-ground is not referenced in live CSS (it is defined nowhere)", () => {
	// Strip /* ... */ comments first — the fix's own comment cites the old token.
	const live = css.replace(/\/\*[\s\S]*?\*\//g, "")
	assert.doesNotMatch(live, /var\(--g-ground\)/, "undefined --g-ground must not be used")
})

test("--g-bg is actually defined in the theme", () => {
	assert.match(themeCss, /--g-bg:\s*#/, "--g-bg must be a defined colour token")
})
