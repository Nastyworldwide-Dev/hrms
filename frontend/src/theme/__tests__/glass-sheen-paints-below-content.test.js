// A decorative overlay must never be painted ON TOP of the text it decorates.
//
// Reported 17 Sep 2026 by an employee, about her own leave balance: "annual
// leave tu nape dia mcm samar samar" — why is the annual leave one faded. Only
// the FIRST tile, on every panel, and nothing was wrong with the data.
//
// `.g-glass::after` is the §6 diagonal gloss: `position: absolute; inset: 0`
// with `linear-gradient(155deg, var(--g-sheen), transparent 40%)`. It carried
// no z-index. A positioned element with `z-index: auto` paints in the
// positioned-descendants layer, which is ABOVE the in-flow, non-positioned
// content of the same box — and `.g-cell`, `.g-balance__number` and every
// other panel child is in-flow and unpositioned. So up to 55% white
// (`--g-sheen` in light mode) was washed over whatever sat in the panel's
// top-left corner, fading out by 40% across it. The first tile lost the
// contrast; the rest kept it.
//
// The page-level twin of this bug was already understood and fixed — see
// `.g-lightfield` (z-index 0) with `.g-page ion-content` lifted to z-index 1.
// The panel-level one was never wired the same way.
//
// Fix: the panel isolates (it already creates a stacking context via
// backdrop-filter, but not in the @supports fallback), and the gloss sits at
// z-index -1 — above the panel's own fill, below everything written on it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8")

/** The declaration block of the first rule whose selector list matches. */
function rule(selectorPattern) {
	const match = css.match(new RegExp(`(^|\\})\\s*([^{}]*${selectorPattern}[^{}]*)\\{([^}]*)\\}`, "m"))
	return match && { selector: match[2].trim(), body: match[3] }
}

test("the diagonal gloss paints beneath the panel's content", () => {
	const gloss = rule("\\.g-glass::after")
	assert.ok(gloss, ".g-glass::after rule must exist")
	assert.match(gloss.body, /background:\s*linear-gradient\(155deg/, "this is the §6 gloss rule")
	assert.match(
		gloss.body,
		/z-index:\s*-1\b/,
		"the gloss must sit below the panel's text, not over it — an employee read " +
			"her own leave balance as faded because of this"
	)
})

test("the panel isolates, so the gloss cannot fall behind the panel itself", () => {
	const panel = rule("\\.g-glass,")
	assert.ok(panel, "the .g-glass base rule must exist")
	assert.match(
		panel.body,
		/isolation:\s*isolate/,
		"backdrop-filter makes a stacking context, but the @supports-not fallback " +
			"drops it — without isolation the z-index -1 gloss would paint behind the ground"
	)
})

test("no full-bleed pseudo-overlay in this stylesheet sits above its own content", () => {
	// A shimmer on a skeleton is exempt: a skeleton is a placeholder shape and
	// never holds text. Every other full-bleed overlay covers something legible.
	const EXEMPT = ["g-skeleton"]
	const offenders = []
	const RULE = /(^|\})\s*([^{}]*::(?:after|before)[^{}]*)\{([^}]*)\}/gm
	for (const [, , selector, body] of css.matchAll(RULE)) {
		const fullBleed = /position:\s*absolute/.test(body) && /inset:\s*0\b/.test(body)
		if (!fullBleed) continue
		if (EXEMPT.some((name) => selector.includes(name))) continue
		if (!/z-index:\s*-\d/.test(body)) offenders.push(selector.trim())
	}
	assert.deepEqual(
		offenders,
		[],
		`these overlays paint over the content they decorate: ${offenders.join(", ")}`
	)
})
