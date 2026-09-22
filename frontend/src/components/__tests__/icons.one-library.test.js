// One icon library, and one vocabulary inside it (plan slice S4).
//
// The app drew icons three ways: `feather-icons` through frappe-ui's
// FeatherIcon, fourteen hand-rolled components under components/icons/, and
// inline <svg> in the pages themselves. Three ways to draw an icon is three
// places to answer "which one do I use?", and the hand-rolled fourteen were
// Lucide glyphs pasted by hand — a copy of a library, maintained by nobody.
//
// WHAT THIS SLICE DOES NOT CLAIM (measured 22 Sep 2026, before any code):
// `feather-icons` does not leave the bundle. It is a dependency of frappe-ui,
// not of this app, and frappe-ui's own Button imports FeatherIcon — the Button
// main.js registers globally and 27 files render. So feather ships whether or
// not we import a single icon from it. The plan's stated revert condition
// ("removes feather-icons in the same commit, or it has made the bundle
// worse") could not be met by any work on this side, and the owner was told
// that and chose to proceed for the vocabulary, not the size. That is recorded
// here because a success condition quietly redefined to fit the work is the
// thing this file exists to prevent.
//
// Source-asserted: these components render inside a Vue app with a router and
// a live session, so the cheap, honest check is over the sources themselves.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.(vue|js)$/.test(entry) && !path.includes("__tests__")) out.push(path)
	}
	return out
}

const FILES = walk(SRC)
const source = (path) => readFileSync(path, "utf8")

// The vocabulary the icon coverage map decided (docs/glass/plan/ICON-COVERAGE-MAP.md).
// `lucide-vue-next` still exports Filter, Trash2, AlertTriangle, CheckCircle,
// Edit and Edit2 as back-compat aliases — verified against the INSTALLED
// package, not its published types. Using one would keep the dead feather
// vocabulary alive in a codebase that just paid to replace it.
const DEAD_ALIASES = ["Filter", "Trash2", "AlertTriangle", "CheckCircle", "Edit2", "Edit"]

test("no file renders a feather icon any more", () => {
	const offenders = FILES.filter((path) => /<FeatherIcon\b/.test(source(path))).map((path) =>
		path.slice(SRC.length)
	)
	assert.deepEqual(offenders, [], "these still draw with feather")
})

test("nothing imports FeatherIcon, not even unused", () => {
	const offenders = FILES.filter((path) => /\bFeatherIcon\b/.test(source(path)))
		.filter((path) => !/GIconButton\.vue$/.test(path)) // names it in a comment explaining why it went
		.map((path) => path.slice(SRC.length))
	assert.deepEqual(offenders, [], "an unused import still pins the dependency")
})

test("the hand-rolled icon components are gone", () => {
	assert.equal(
		existsSync(join(SRC, "components/icons")),
		false,
		"components/icons/ was fourteen Lucide glyphs pasted by hand; the package draws them now"
	)
})

test("no dead feather name survives as a lucide alias", () => {
	const offenders = []
	for (const path of FILES) {
		const imports =
			source(path).match(/import\s*\{([^}]*)\}\s*from\s*["']lucide-vue-next["']/gs) || []
		for (const block of imports) {
			for (const alias of DEAD_ALIASES) {
				if (new RegExp(`\\b${alias}\\b`).test(block))
					offenders.push(`${path.slice(SRC.length)}: ${alias}`)
			}
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"the map decided these: funnel, trash, triangle-alert, circle-check, square-check, pen-line, pencil"
	)
})

// Every icon this app draws must carry the theme, or dark mode paints an icon
// the same colour in both themes. Feather's component did this for free; a
// bare lucide import does not, so it is now this app's own rule.
test("every lucide icon inherits the theme colour", () => {
	const offenders = []
	for (const path of FILES) {
		if (!/lucide-vue-next/.test(source(path))) continue
		const text = source(path)
		for (const tag of text.matchAll(/<([A-Z]\w+)\b[^>]*\/?>/g)) {
			const whole = tag[0]
			if (!/class=/.test(whole)) continue
			if (
				/\bstroke="(?!currentColor)/.test(whole) ||
				/\bfill="(?!none|currentColor)/.test(whole)
			) {
				offenders.push(`${path.slice(SRC.length)}: ${tag[1]} pins a colour`)
			}
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"an icon that pins a colour is invisible in one of the two themes"
	)
})
