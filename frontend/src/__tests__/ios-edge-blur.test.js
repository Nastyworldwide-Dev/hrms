// 27 Oct 2026 (owner screenshot: the top bar "looks blurry" on iPhone). Not our
// CSS: iOS 26 draws its own Liquid Glass blur over the top ~40 pt of an
// installed web app, and no meta tag turns it off. WebKit leaves it out when a
// fixed or sticky, opaque, full-width container sits at the top edge. So, in
// the installed iPhone app only, the bar is pinned and painted the page ground
// (the same colour it already shows through, so it looks the same).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(fileURLToPath(new URL("../theme/glass-components.css", import.meta.url)), "utf8")

test("in the installed iPhone app the top bar is pinned and opaque", () => {
	const at = css.indexOf("@media (display-mode: standalone)")
	assert.ok(at > 0, "a standalone-only rule")
	const block = css.slice(at, css.indexOf("\n}\n", at))
	assert.match(block, /@supports \(-webkit-touch-callout: none\)/, "iOS only")
	assert.match(block, /\.g-page ion-header\.header-ios,\s*\.g-page \.g-header,\s*\.g-header \{[^}]*position: sticky;[^}]*top: 0;[^}]*z-index: var\(--g-layer-bar\);[^}]*background: var\(--g-bg\);/)
})
