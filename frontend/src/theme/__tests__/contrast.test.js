// WCAG 2.2 AA (1.4.3 text, 1.4.11 non-text) guard for BOTH themes.
//
// The failure this pins: cards used --g-track-solid (the solid bar-track) as
// their surface. In dark that #313133 slab read as a heavy grey box AND dropped
// tertiary TEXT (--g-ink-muted) to 3.41:1; in light the #ECEDEF track was
// darker than the page and dropped it to 4.14:1 — both below the 4.5:1 text
// floor. The fix decoupled bg-surface onto --g-surface (the glass tone) in the
// TOKEN SOURCE (design/tokens.json), not by hand-editing this generated CSS and
// not by darkening text: --g-ink3 stays as designed (non-text: chevrons,
// dividers, disabled — 3:1 bar).
//
// This reads the generated dark AND light token triples and asserts tertiary
// text clears 4.5:1 and the non-text tier clears 3:1 on the surface, in both
// themes, so a future edit that reheavies the surface or darkens the text past
// the line fails the build.

import assert from "node:assert"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

const CSS = fs.readFileSync(
	path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "glass.css"),
	"utf8",
)

// Every "R G B" triple for a token, in source order. The light :root block is
// declared first, the dark override second — so [0] is light, [last] is dark.
function triples(name) {
	const all = [...CSS.matchAll(new RegExp(`--${name}:\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)`, "g"))]
	assert.ok(all.length >= 2, `token --${name} needs light+dark definitions`)
	return { light: pick(all[0]), dark: pick(all[all.length - 1]) }
}
const pick = (m) => [Number(m[1]), Number(m[2]), Number(m[3])]

function relLum([r, g, b]) {
	const f = (c) => {
		c /= 255
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
	}
	return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
function contrast(fg, bg) {
	const [hi, lo] = [relLum(fg), relLum(bg)].sort((a, b) => b - a)
	return (hi + 0.05) / (lo + 0.05)
}

const AA_TEXT = 4.5
const AA_NONTEXT = 3.0
const surface = triples("g-surface-rgb")
const muted = triples("g-ink-muted-rgb")
const ink3 = triples("g-ink3-rgb")

for (const theme of ["light", "dark"]) {
	test(`${theme}: tertiary text (ink-muted) on the card surface clears WCAG AA (4.5:1)`, () => {
		const r = contrast(muted[theme], surface[theme])
		assert.ok(r >= AA_TEXT, `ink-muted on surface is ${r.toFixed(2)}:1, need ${AA_TEXT}:1`)
	})
	test(`${theme}: non-text tier (ink3) on the card surface clears 3:1`, () => {
		const r = contrast(ink3[theme], surface[theme])
		assert.ok(r >= AA_NONTEXT, `ink3 on surface is ${r.toFixed(2)}:1, need ${AA_NONTEXT}:1`)
	})
}

test("dark card surface is NOT the heavy #313133 bar-track (49 49 51)", () => {
	assert.ok(surface.dark[0] < 49, `dark surface R is ${surface.dark[0]}, expected the glass tone (<49)`)
})

test("light card surface is a lift ABOVE the page, not the darker #ECEDEF track", () => {
	// #ECEDEF = 236 — the track that sat darker than the page. The glass tone lifts above it.
	assert.ok(surface.light[0] > 236, `light surface R is ${surface.light[0]}, expected a lift (>236)`)
})
