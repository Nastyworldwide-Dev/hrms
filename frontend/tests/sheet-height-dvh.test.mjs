// A sheet is measured against the viewport the browser is actually showing
// (plan slice S7).
//
// `100vh` is the LARGE viewport: the height the page would have if the mobile
// browser's address bar were fully retracted. On Android Chrome and iOS Safari
// the bar is showing most of the time, so `100vh` is taller than the window —
// and a sheet sized `calc(100vh - 5rem)` runs off the bottom of the screen by
// roughly the height of that bar. Its last row, which on every sheet in this
// app is the confirm button, sits under the browser chrome.
//
// `100dvh` is the DYNAMIC viewport: what is visible right now, bar or no bar.
// It is what a sheet wants. The fallback line above it is not decoration —
// a browser that does not know `dvh` drops the whole declaration, so the
// property would be unset rather than merely less accurate.
//
// §15 forbids animating anything but transform and opacity, and `dvh` changes
// value as the bar slides. That is a repaint the spec did not budget for, so
// the sheet's max-height is the only place this unit is allowed: a scroll
// container that resizes is correct; a glass panel that resizes mid-scroll is
// the recomposition §15 exists to prevent.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../src", import.meta.url))

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.(vue|css)$/.test(entry)) out.push(path)
	}
	return out
}

const FILES = walk(SRC)

// Strip comments before counting. A comment that NAMES the unit it is warning
// about is documentation, not a violation — the same defect the usage gate
// already had, where a component explaining which primitive owns its surface
// scored as using that surface. Both block styles, and `//` only when it is
// not inside a url() or a protocol.
function read(path) {
	return readFileSync(path, "utf8")
		.replace(/<!--[\s\S]*?-->/g, (block) => block.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (block) => block.replace(/[^\n]/g, " "))
		.replace(
			/(^|[^:])\/\/[^\n]*/g,
			(line, lead) => lead + " ".repeat(line.length - lead.length)
		)
}

test("no sheet is measured against the large viewport", () => {
	const offenders = []
	for (const path of FILES) {
		for (const line of read(path).split("\n")) {
			if (!line.includes("100vh")) continue
			// The fallback line is the point: it must stay, and it is the one
			// place `100vh` is still correct, because a browser reading it is
			// a browser with no better answer.
			if (/--g-sheet-max-height:\s*calc\(100vh/.test(line)) continue
			offenders.push(`${path.slice(SRC.length)}: ${line.trim()}`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"use the dynamic viewport (dvh); the address bar eats the difference"
	)
})

test("the sheet token declares dvh with a vh fallback, in that order", () => {
	const css = read(join(SRC, "theme/glass.css"))
	const fallback = css.indexOf("--g-sheet-max-height: calc(100vh")
	const real = css.indexOf("--g-sheet-max-height: calc(100dvh")
	assert.ok(
		fallback >= 0,
		"the vh line must stay: a browser without dvh would otherwise have nothing"
	)
	assert.ok(real >= 0, "the dvh line must exist")
	assert.ok(
		fallback < real,
		"the fallback comes FIRST; the last declaration a browser understands wins"
	)
})

test("only the sheet may resize with the address bar", () => {
	// §15: glass surfaces do not resize with the address bar,
	// because either would force a per-frame recomposition of every layer
	// above them. A `dvh` anywhere else in the glass layer is exactly that.
	const offenders = []
	for (const path of FILES) {
		for (const line of read(path).split("\n")) {
			// NOT /\bdvh\b/: a CSS length is a number glued to its unit, and
			// there is no word boundary between `0` and `d`, so `50dvh` never
			// matched at all. Found by a mutant that added exactly that and
			// survived — the rule had a hole its own author could not see.
			if (!/\d(?:dvh|svh|lvh)\b/.test(line)) continue
			// The sheet's own token, and the one view that positions ITSELF a
			// viewport down (InstallPrompt's margin-top) — a margin moves a
			// box, it does not resize a compositing layer.
			if (/--g-sheet-max-height/.test(line)) continue
			if (/mt-\[calc\(100dvh/.test(line)) continue
			offenders.push(`${path.slice(SRC.length)}: ${line.trim()}`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"a surface that resizes as the bar slides repaints every layer above it"
	)
})
