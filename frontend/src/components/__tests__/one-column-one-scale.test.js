// Sizes come from the system, not from a call site (revamp slice A3, §8 V3).
//
// Measured on 22 Sep 2026: 103 arbitrary Tailwind values across components and
// views, 19 of them numbers that exist in no token. The two worst classes:
//
//   ICONS. The same glyph was drawn at 15, 17, 18, 19, 22, 30 and 34px
//   depending on which screen it was on. Nobody chose seven sizes; each call
//   site picked one and the next copied it. §9 says icons are drawn on a 16
//   grid, so there is a right answer and it was not in the code.
//
//   THE DESKTOP COLUMN. §20.3 specifies ONE content column, signed off at
//   720px. Five screens each invented their own — Profile, Notifications and
//   AppSettings at 620, RemoteApprovals at 680, SopDetail at 820 — so a person
//   moving between them on a laptop watched the page width change under them.
//
// A long-form READING column is a genuinely different measure (Bringhurst:
// 45–75 characters), so it gets its own token rather than being forced onto
// the app column. Both are 720px today; the point is that changing one must
// not silently move the other.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const tokens = JSON.parse(readFileSync(join(SRC, "../../design/tokens.json"), "utf8"))

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__") walk(path, out)
		} else if (/\.vue$/.test(entry)) out.push(path)
	}
	return out
}

const FILES = [...walk(join(SRC, "components")), ...walk(join(SRC, "views"))]
const read = (p) => readFileSync(p, "utf8")
const rel = (p) => p.slice(SRC.length).replace(/^\/+/, "")

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
}

test("no component sizes an icon with a number", () => {
	// w-[18px] is a decision taken in a template, which means it is a decision
	// nobody can find later. The icon group is where glyph sizes live.
	const offenders = []
	for (const file of FILES) {
		for (const m of code(read(file)).matchAll(/\b[wh]-\[(\d+)px\]/g)) {
			offenders.push(`${rel(file)}: ${m[0]}`)
		}
	}
	assert.deepEqual(offenders, [], "use w-icon-sm / icon-md / icon-lg / icon-xl / control-lg")
})

test("the icon sizes are a scale, and they are on the grid", () => {
	const icons = tokens.icon
	assert.ok(icons, "there is an icon token group")
	const px = Object.entries(icons).map(([k, v]) => [k, parseFloat(v.value)])
	for (const [name, value] of px) {
		assert.equal(value % 4, 0, `icon.${name} = ${value}px is off the 4pt grid`)
	}
	// §9's own grid is the smallest step; nothing smaller may exist.
	assert.equal(icons["icon-sm"].value, "16px", "§9 draws line icons on a 16 grid")
	// The platform floor is not ours to shrink.
	assert.equal(icons["control-md"].value, "44px", "HIG 44pt / Material 48dp")
})

test("every screen uses the ONE desktop column", () => {
	// Five screens each carried their own max-width. The failure mode is not
	// ugliness — it is that the page jumps width as you navigate, which reads
	// as the app being broken rather than as a design choice.
	const offenders = []
	for (const file of FILES) {
		for (const m of code(read(file)).matchAll(/max-w-\[(\d+)px\]/g)) {
			offenders.push(`${rel(file)}: ${m[0]}`)
		}
	}
	assert.deepEqual(offenders, [], "use max-w-content-column-lg, or -read for long-form")
})

test("the reading column is held apart from the app column", () => {
	// They are equal today. That is a coincidence of values, not of meaning: a
	// reading measure is set by characters per line and an app column by
	// layout, so one token would let a layout change silently break a measure.
	const app = tokens.layout["content-column-lg"]
	const read_ = tokens.layout["content-column-read"]
	assert.ok(read_, "the reading column exists")
	assert.match(read_.description, /45-75|characters/i, "and says what sets it")
	assert.notEqual(app.description, read_.description, "two reasons, written down")
})

test("the modal backdrop reads the layer scale", () => {
	// z-[10000] was written by hand next to a token holding exactly 10000.
	// Nothing connected them, so re-ordering the scale would have left the
	// backdrop behind.
	const modal = code(read(join(SRC, "components/CustomIonModal.vue")))
	assert.doesNotMatch(modal, /z-\[\d+\]/, "no hand-written stacking level")
	assert.match(modal, /z-scrim-backdrop/, "it reads the scale")
	assert.ok(tokens.layer["scrim-backdrop"], "which has an entry for it")
})
