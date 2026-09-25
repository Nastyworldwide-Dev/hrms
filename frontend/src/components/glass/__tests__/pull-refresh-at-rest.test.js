// alpha.8 (owner, 25 Sep 2026, iOS 26: "laggy when I pull down or scroll";
// and "Pull to refresh" printed under the Today title at rest, owner's
// screenshot). The refresher sits ABOVE the page (z-index 2) and its shimmer
// bar looped forever; visibility:hidden hides it but does NOT stop the
// animation, so a compositing layer over the page repainted every frame.
// At rest it is now not painted at all, and the shimmer runs only while
// actually refreshing.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const root = postcss.parse(readFileSync(fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)), "utf8"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("at rest the refresher is not painted", () => {
	assert.equal(decls("ion-refresher:not(.refresher-active) .g-refresh").display, "none")
})

test("the shimmer runs only while refreshing", () => {
	assert.equal(decls(".g-refresh__fill").animation, undefined)
	assert.match(decls("ion-refresher.refresher-refreshing .g-refresh__fill").animation || "", /g-indeterminate/)
})
