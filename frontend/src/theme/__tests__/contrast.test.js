// WCAG 2.2 AA (1.4.3) guard for dark-mode text on the card surface.
//
// The failure this pins: cards once used --g-track-solid (#313133, the solid
// bar-track) as their background, which read as a heavy grey slab AND dropped
// muted text to 3.41:1. The fix decoupled bg-surface onto --g-surface (the
// glass tone) and lifted the faint tier. This test reads the DARK token values
// straight from glass.css and asserts muted + faint text clear 4.5:1 on the
// surface, so a future edit that darkens the text or lightens the surface
// past the AA line fails the build instead of shipping washed-out UI.

import assert from "node:assert"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

const CSS = fs.readFileSync(
	path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "glass.css"),
	"utf8",
)

// The dark block is the second :root-level declaration set. Read a token's
// "R G B" triple from within it (the later definition wins in the cascade,
// which is the dark override).
function darkTriple(name) {
	const all = [...CSS.matchAll(new RegExp(`--${name}:\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)`, "g"))]
	assert.ok(all.length >= 1, `token --${name} not found`)
	const m = all[all.length - 1] // dark override is declared after light
	return [Number(m[1]), Number(m[2]), Number(m[3])]
}

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

const AA = 4.5
const surface = darkTriple("g-surface-rgb")
const muted = darkTriple("g-ink-muted-rgb")
const ink3 = darkTriple("g-ink3-rgb")

test("dark: secondary text (ink-muted) on the card surface clears WCAG AA", () => {
	const ratio = contrast(muted, surface)
	assert.ok(ratio >= AA, `ink-muted on surface is ${ratio.toFixed(2)}:1, need ${AA}:1`)
})

test("dark: faint text (ink3) on the card surface clears WCAG AA", () => {
	const ratio = contrast(ink3, surface)
	assert.ok(ratio >= AA, `ink3 on surface is ${ratio.toFixed(2)}:1, need ${AA}:1`)
})

test("dark: the card surface is NOT the heavy #313133 bar-track slab", () => {
	// #313133 = 49 49 51 — the value that failed. The surface must be darker.
	assert.ok(surface[0] < 49, `surface R is ${surface[0]}, expected the glass tone (<49)`)
})
