// At lg: the side nav carries the "n Nadi" mark, so the header's logo tile is
// hidden there, as its avatar already is (UX review 21 Oct 2026, F11).
// Run: cd frontend && node --test src/components/glass/__tests__/GAppHeader.desktop-logo.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)), "utf8")

test("the header's logo hides at lg: with the avatar", () => {
	assert.match(
		css,
		/@media \(min-width: 1024px\) \{[^}]*\.g-header__avatar-link,\s*\.g-header > \.g-logo-mark \{\s*display: none;/
	)
})
