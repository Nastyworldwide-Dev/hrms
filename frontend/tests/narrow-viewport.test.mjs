// Nothing assumes a screen wider than the narrowest phone (pre-2.0 R5,
// checklist §3: "works from approximately 320px width upward", "no unintended
// horizontal scrolling").
//
// The app is designed against a 360x640 budget (home-fold-budget.test.js) and
// measured at 390x844. 320 is narrower than either, and nothing in the repo
// has ever checked it — so a fixed width, a min-width, or a grid that needs
// four columns would overflow sideways on a Galaxy A-series or an SE and
// nobody would know until an employee said the screen "goes sideways".
//
// THIS IS A SOURCE CHECK, NOT A MEASUREMENT, and it is the honest half of R5.
// The real numbers need a running site and there is none reachable from here
// (owner, 22 Sep 2026: "if site is inaccessible its okay"). What can be
// asserted without a browser is that no rule PROMISES more width than 320
// gives: a `w-[380px]` cannot fit, whatever the layout around it does. The
// measurement harness (e2e/app-measure.mjs) already takes W and H from the
// environment, so the pixel truth is one command away once a site exists:
//     W=320 H=640 node e2e/app-measure.mjs
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const FRONTEND = join(fileURLToPath(new URL(".", import.meta.url)), "..")
const SRC = join(FRONTEND, "src")

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.(vue|css)$/.test(entry) && !path.includes("__tests__"))
			out.push(path)
	}
	return out
}

// Comments stripped: a comment explaining a width names that width, and five
// separate gates in this repo have already counted their own documentation.
function code(path) {
	return readFileSync(path, "utf8")
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(
			/(^|[^:])\/\/[^\n]*/g,
			(l, lead) => lead + " ".repeat(l.length - lead.length)
		)
}

const FILES = walk(SRC)

/** `text` with every `@media (...)` condition blanked. */
function declarationsOnly(text) {
	return text.replace(/@media[^{]*/g, (q) => q.replace(/[^\n]/g, " "))
}

//: The narrowest screen the checklist names. A rule that needs more than this
//: much room, unconditionally, overflows on a real phone people carry.
const FLOOR = 320

test("nothing demands more width than the narrowest phone has", () => {
	const offenders = []
	for (const path of FILES) {
		const text = code(path)
		// `min-width: 380px`, `min-w-[380px]`, `width: 400px` — an absolute
		// floor wider than the screen. A max-width is fine: it caps, never
		// demands.
		//
		// NOT inside an @media query, which is the opposite thing: there
		// `min-width: 1024px` means "once the screen is this wide", and every
		// breakpoint in the app tripped the first version of this rule. The
		// same two words mean "at least this much room is available" in a
		// query and "this element needs at least this much" in a declaration.
		for (const m of declarationsOnly(text).matchAll(
			/\bmin-width:\s*(\d+)px/g
		)) {
			if (Number(m[1]) > FLOOR)
				offenders.push(`${path.slice(SRC.length)}: min-width ${m[1]}px`)
		}
		for (const m of text.matchAll(/\bmin-w-\[(\d+)px\]/g)) {
			if (Number(m[1]) > FLOOR)
				offenders.push(`${path.slice(SRC.length)}: min-w-[${m[1]}px]`)
		}
		// A fixed width on a block that is meant to fill the screen. Scoped to
		// px because a % or a vw cannot overflow by itself.
		// `(?<![-\w])width:` — not `--width:` or `--g-viewport-width:`. A custom
		// property is a VALUE somebody may or may not use, and both in this app
		// are legitimate: GModal's --width is inside an lg: query and capped by
		// --max-width beside it, and --g-viewport-width is the reference phone
		// the measurement harness is pointed at, not a box anything renders.
		for (const m of declarationsOnly(text).matchAll(
			/(?<![-\w])width:\s*(\d+)px/g
		)) {
			if (Number(m[1]) > FLOOR)
				offenders.push(`${path.slice(SRC.length)}: width ${m[1]}px`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		`nothing may be wider than ${FLOOR}px unconditionally`
	)
})

test("the horizontal axis is never the one that scrolls", () => {
	// `overflow-x: auto|scroll` on a page-level container is how a layout that
	// does not fit hides the fact. On a TABLE or a deliberately scrollable
	// strip it is a legitimate pattern, so this pins the rule at the app
	// shell: the body and the page wrapper never scroll sideways.
	const css =
		code(join(SRC, "theme/glass-components.css")) +
		code(join(SRC, "theme/glass.css"))
	const page = css.slice(
		css.indexOf("\n.g-page {"),
		css.indexOf("}", css.indexOf("\n.g-page {"))
	)
	assert.doesNotMatch(
		page,
		/overflow-x:\s*(auto|scroll)/,
		".g-page must not absorb a too-wide child"
	)
})

test("the measurement harness can be pointed at the narrow phone", () => {
	// R5's real deliverable while no site is reachable: the tool takes the
	// viewport from the environment, so the numbers are one command away
	// rather than a rewrite away.
	const harness = readFileSync(join(FRONTEND, "e2e/app-measure.mjs"), "utf8")
	assert.match(harness, /process\.env\.W/, "width is overridable")
	assert.match(harness, /process\.env\.H/, "and height")
	// And it records the tab bar, which the 2026-09-09 baseline did not —
	// every overflow in that file is understated by the bar's height because
	// it was captured before the nav was repaired.
	assert.match(
		harness,
		/tabH/,
		"the tab bar is measured, not assumed to be zero"
	)
})

test("the stale baseline is marked stale, not quietly trusted", () => {
	// docs/glass/audit/2026-09-09-app-measure.json records tabH: 0 on every
	// screen. Every 'overflow' in it is therefore ~65px too small, and the 2.0
	// plan rests on those numbers. A reader must not be able to pick the file
	// up without learning that.
	const audit = join(
		FRONTEND,
		"../docs/glass/audit/2026-09-09-app-measure.json"
	)
	const raw = readFileSync(audit, "utf8")
	const data = JSON.parse(raw)
	assert.ok(
		data.stale,
		"the file must say so in its own data, not only in a plan nobody opens"
	)
	assert.match(data.stale, /tabH|tab bar/i, "and say why")
})
