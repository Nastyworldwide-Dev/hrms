// alpha.7 Phase 3 (plan §5.3; reviews A4, B25): the empty state is iOS's
// ContentUnavailableView — a large grey symbol, a 22 pt bold title and a
// 15 pt secondary line, centred, with NO box (Nadi drew a dashed box with
// 13 pt / 11 pt text, and 11 pt is below Apple's smallest body size).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const src = read("../GEmptyState.vue")
const root = postcss.parse(read("../../../theme/glass-components.css"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("a symbol above the words; a default when the caller gives none", () => {
	assert.match(src, /<component :is="icon \|\| Inbox" class="g-empty__icon" aria-hidden="true"/)
	assert.match(src, /icon: \{ type: \[Object, Function\], default: null \}/)
})

test("no box; iOS type sizes", () => {
	const box = decls(".g-empty")
	assert.ok(!box.border, `border: ${box.border}`)
	assert.equal(decls(".g-empty__title")["font-size"], "22px")
	assert.equal(decls(".g-empty__body")["font-size"], "15px")
	assert.equal(decls(".g-empty__icon").width, "48px")
})
