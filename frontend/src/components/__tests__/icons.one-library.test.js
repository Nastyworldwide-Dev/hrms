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
		.filter((path) => !path.endsWith("GIconButton.vue")) // names it in a comment explaining why it went
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

// The fourteen hand-rolled components every one drew at stroke-width 1.5, and
// Lucide's own default is 2 — a 33% heavier line on every nav tab, side-nav
// item and Home quick link, which is a visible change and was not one anybody
// asked for. Design review of bed29bbee found it; the weight is now set once,
// globally, rather than passed at ~40 call sites where one omission is a
// mismatched icon nobody notices.
test("migrated icons keep the weight the hand-rolled ones drew at", () => {
	// Not in main.js: the package's `defaultAttributes` are module-internal
	// and not exported, so there is nothing to assign. Every icon it renders
	// does carry a `lucide` class, so CSS is the one global lever — and it is
	// where §9's own weight is already set.
	const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
	assert.match(
		css,
		/svg\.lucide\s*\{[^}]*stroke-width:\s*1\.5/,
		"2 is a third heavier than the fourteen components this set replaced"
	)
})

// ...and nothing may quietly opt back out of it. A call site that passes its
// own stroke-width is the drift the global default exists to stop.
test("no call site overrides the icon weight", () => {
	const offenders = []
	for (const path of FILES) {
		if (!/lucide-vue-next/.test(source(path))) continue
		for (const tag of source(path).matchAll(/<[A-Z]\w+\b[^>]*\/?>/g)) {
			if (/:?stroke-width=|:strokeWidth=/.test(tag[0])) offenders.push(path.slice(SRC.length))
		}
	}
	assert.deepEqual(offenders, [], "the weight is a system decision, not a per-icon one")
})

// The one glyph of the fourteen that was NOT a Lucide icon pasted by hand:
// ExpenseIcon drew a dollar COIN on a "-1 -1 28 28" viewBox, from Streamline
// (its group id is that library's slug), and it went out as Lucide's Receipt
// — a torn-paper receipt. A different picture for the same idea, changed
// silently in a commit whose whole claim was that nothing but the source
// changed. Design review of bed29bbee caught it; `CircleDollarSign` is the
// coin the app actually had.
//
// The other thirteen were checked the same way and are genuine: six carry
// Lucide's own `class="lucide lucide-*"` marker, and the remaining seven draw
// Lucide's geometry (headphones, chart-line, kanban, life-buoy, circle-check,
// external-link, user-check) on its 24-grid.
test("the expenses glyph is still a coin, not a receipt", () => {
	// The expense link moved from Home to Requests (2.0 slice 1.3). The RULE is
	// unchanged — the Expenses glyph is the coin the app had, not a receipt —
	// and this follows it to the two files that draw it now.
	for (const file of ["views/Requests.vue", "data/navItems.js"]) {
		const text = readFileSync(join(SRC, file), "utf8")
		assert.match(text, /\bCircleDollarSign\b/, `${file} should draw the coin the app had`)
		// `Receipt` may legitimately appear for a DIFFERENT link — Requests uses
		// it for "Claim Overtime", which is a receipt-shaped idea. What must
		// not happen is the EXPENSES row taking it back.
		// The whole ENTRY — from its opening brace to its label. An entry may be
		// one line or five depending on how the formatter last wrapped it, so
		// neither a line match nor a fixed-width window is reliable: the first
		// looked at the wrong line, the second stopped before the icon.
		for (const label of ['__("Claim an Expense")', 'title: "Expenses"']) {
			const at = text.indexOf(label)
			if (at < 0) continue
			const entry = text.slice(text.lastIndexOf("{", at), at)
			assert.doesNotMatch(entry, /\bReceipt\b/, `${file}: Receipt is a different pictogram`)
		}
	}
})
