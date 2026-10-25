// Owner, 25 Oct 2026: the must-read tick "didn't look like what it should be" — the browser drew
// its own blue-on-white box (screenshot: accent-color did not reach it), the only native-looking
// control in a Glass page whose button beside it is lime. The box is drawn by us: a rounded ink3
// outline, lime fill + on-brand tick when ticked, dimmed when closed. The input stays the real
// control, so focus, keyboard and VoiceOver are unchanged.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(fileURLToPath(new URL("../../../theme/glass-components.css", import.meta.url)), "utf8")
const root = postcss.parse(css)
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("the tick box is drawn by Glass, not the browser", () => {
	const box = decls(".g-check .g-check__box")
	assert.equal(box.appearance, "none")
	assert.equal(box["-webkit-appearance"], "none")
	// ink2: ink3 is 2.93:1 on the light page ground (design review of a68b4dcb5)
	assert.match(box.border, /var\(--g-ink2\)/)
	assert.ok(box["border-radius"], "rounded like the rest of Glass")
	// the plugin's :checked:focus/:checked:hover rules are (0,3,0) and fill with currentColor
	assert.equal(box.color, "var(--g-brand)")
})

test("ticked = lime fill with a dark tick (the Confirm button's colours)", () => {
	const on = decls(".g-check .g-check__box:checked")
	assert.equal(on["background-color"], "var(--g-brand)")
	// the outline stays: a lime edge is 1.06:1 on the light page and the box shape vanished
	assert.equal(on["border-color"], undefined)
	const tick = decls(".g-check .g-check__box:checked::after")
	assert.match(tick.border, /var\(--g-on-brand\)/)
	assert.equal(on["background-image"], "none", "no plugin tick drawn under ours")
})

// Tailwind's forms plugin loads after glass-components.css and styles [type="checkbox"] (0,1,0)
// and [type="checkbox"]:checked/:focus (0,2,0). A rule that only ties loses, which is how the
// first fix still drew a blue box in the browser. Every box rule is one class above the plugin.
test("every tick-box rule outranks the forms plugin", () => {
	root.walkRules((r) => {
		for (const sel of r.selectors.filter((x) => x.includes("g-check__box")))
			assert.ok(sel.startsWith(".g-check .g-check__box"), `${sel} ties with [type="checkbox"]`)
	})
	const focus = decls(".g-check .g-check__box:focus")
	assert.equal(focus["box-shadow"], "none", "no blue ring after a tap")
	assert.equal(decls(".g-check .g-check__box:focus-visible")["box-shadow"], "var(--g-shadow-focus-ring)")
})

test("a closed tick reads as closed", () => {
	assert.ok(decls(".g-check .g-check__box:disabled").opacity, "dimmed while the end is not reached")
})

test("high contrast mode keeps the ticked state", () => {
	let found = false
	root.walkAtRules("media", (m) => {
		if (!m.params.includes("forced-colors: active")) return
		m.walkRules((r) => {
			if (r.selector === ".g-check .g-check__box:checked") {
				found = true
				r.walkDecls("background-color", (d) => assert.equal(d.value, "Highlight"))
			}
		})
	})
	assert.ok(found)
})
