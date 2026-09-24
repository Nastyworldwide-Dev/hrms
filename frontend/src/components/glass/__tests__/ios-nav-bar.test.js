// alpha.7 Phase 1 (plan §5.1, reviews A1, A8-A10, B24): the iOS navigation bar.
// Tab roots: large title, 34 pt bold, leading (HIG "Large titles").
// Pushed screens: Back leading, a 17 pt semibold title CENTRED, only the
// screen's own actions trailing; no bell or avatar (they belong to the roots).
// Bar buttons are round 44 pt; the avatar is a circle (Apple ID / Contacts).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const header = read("../GAppHeader.vue")
const root = postcss.parse(read("../../../theme/glass-components.css"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("a tab root has a large title; a pushed screen an inline, centred one", () => {
	assert.match(header, /'g-header--large': !showBack/)
	assert.match(header, /'g-header--inline': showBack/)
	const large = decls(".g-header--large .g-header__title")
	assert.equal(large["font-size"], "34px")
	assert.equal(large["font-weight"], "700")
	const inline = decls(".g-header--inline .g-header__title")
	assert.equal(inline["font-size"], "17px")
	assert.equal(inline["font-weight"], "600")
	assert.equal(inline["text-align"], "center")
})

test("bell and avatar only on tab roots", () => {
	assert.match(header, /<template v-else-if="!showBack">/)
})

test("bar buttons are round 44 pt; the avatar is a circle", () => {
	assert.equal(decls(".g-header .g-iconbtn")["border-radius"], "50%")
	assert.equal(decls(".g-header__action")["border-radius"], "50%")
	assert.match(header, /<GAvatar[^>]*\bround\b/)
})
