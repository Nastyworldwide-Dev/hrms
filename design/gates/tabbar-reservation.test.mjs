// The floating tab bar and the scroll padding that keeps content off it are
// computed from the same tokens on purpose — glass-components.css says so in
// its own comment: "if the height were left intrinsic the two could drift and
// content would silently slide back under the bar."
//
// They drifted anyway, because the bar does not obey the height it is given.
// Ionic's tab-bar host carries `box-sizing: content-box !important`
// (@ionic/core tab-bar.md.css), which light DOM cannot override. So
// `height: var(--g-tabbar-height)` sizes the CONTENT box only, and the bar's
// rendered height is that plus its own vertical padding and border, on both
// edges:
//
//     64 (token) + 11 + 9 (padding) + 1 + 1 (border) = 86px rendered
//     64 (token) + 2*9 (gap)                         = 82px reserved (was)
//
// Four pixels of every scrollable tab screen came to rest under the glass at
// maximum scroll, with nowhere further to scroll. That is CLASS H of the
// mockup-4 audit ("text resting under chrome"), reproduced in the shipped app.
//
// This asserts the RELATIONSHIP, never either number, and asserts it the same
// way the rest of this directory closed the copied-input class: every part of
// the bar's rendered box must be a NAMED token in design/tokens.json, the bar
// must draw from that token rather than a literal, and the reservation must
// read the same name. A literal in either place is invisible to the other.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);
const css = readFileSync(join(ROOT, "..", "frontend", "src", "theme", "glass-components.css"), "utf8");
const tokens = JSON.parse(readFileSync(join(ROOT, "tokens.json"), "utf8"));

// A selector may be one of SEVERAL in a comma-separated list — the reservation
// needs a second, more specific selector to beat `.ion-no-padding` (see the
// specificity test below), and the first version of this matched only a
// selector standing alone, so adding that second one made the guard report the
// rule missing entirely.
const rule = (selector) => {
	const re = new RegExp(`(?:^|\\n)${selector}\\s*(?:,[^{]*)?\\{([\\s\\S]*?)\\n\\}`);
	const m = re.exec(css);
	assert.ok(m, `glass-components.css has no \`${selector}\` rule`);
	return m[1];
};

// the parts of the bar's rendered box that --g-tabbar-height does NOT cover,
// because content-box excludes them
const PARTS = ["tabbar-pad-top", "tabbar-pad-bottom", "tabbar-border"];

test("every part of the bar's box that content-box excludes is a token, not a literal", () => {
	for (const name of PARTS) {
		const v = tokens.layout?.[name]?.value;
		assert.ok(v, `design/tokens.json layout['${name}'] is missing`);
		assert.match(v, /^\d+(\.\d+)?px$/, `layout['${name}'] = "${v}" must be an exact px length`);
	}
});

test("the bar draws its padding and border from those tokens", () => {
	const bar = rule("ion-tab-bar\\.g-tabbar");

	const pad = /padding:\s*([^;]+);/.exec(bar);
	assert.ok(pad, "the bar rule declares no padding");
	assert.match(
		pad[1],
		/var\(--g-tabbar-pad-top\)[\s\S]*var\(--g-tabbar-pad-bottom\)/,
		`the bar's padding is "${pad[1].trim()}". A literal here is invisible to the ` +
			"reservation below, which is how content ended up under the bar.",
	);

	const border = /border:\s*([^;]+);/.exec(bar);
	assert.ok(border, "the bar rule declares no border");
	assert.match(
		border[1],
		/var\(--g-tabbar-border\)/,
		`the bar's border width is "${border[1].trim()}"; it counts toward the rendered ` +
			"height under content-box and must be readable by the reservation",
	);

	assert.match(bar, /height:\s*var\(--g-tabbar-height\)/, "the bar must still pin its content height");
});

test("ion-content reserves the bar's WHOLE rendered box, not just its content height", () => {
	const reserve = rule("ion-tabs \\.g-page ion-content");
	const calc = /--padding-bottom:\s*calc\(([\s\S]*?)\);/.exec(reserve);
	assert.ok(calc, "the reservation must be a calc() over the bar's own tokens");
	const expr = calc[1];

	for (const name of ["tabbar-height", ...PARTS])
		assert.ok(
			expr.includes(`--g-${name}`),
			`the reservation does not account for --g-${name}. Ionic forces content-box on ` +
				"the bar host, so the rendered bar is taller than --g-tabbar-height and content " +
				`comes to rest under it. Reservation reads: calc(${expr.trim()})`,
		);

	// both edges, not one — content-box adds a border on the top AND the bottom
	assert.match(
		expr,
		/2\s*\*\s*var\(--g-tabbar-border\)/,
		"a 1px border adds 2px to rendered height, not 1px: the reservation must count both edges",
	);
});

test("the reservation outranks Ionic's .ion-no-padding", () => {
	// THE DEFECT THIS EXISTS FOR, deployed 23 September 2026.
	//
	// BaseLayout puts `.ion-no-padding` on every ion-content, and Ionic's
	// utility sets `--padding-bottom: 0`. A class beats an element+descendant
	// selector, so the whole calc() above evaluated to nothing and every tab
	// screen with content past the fold ended behind the glass — the Calendar's
	// "Claim Overtime or Leave" row was photographed unreachable under the bar.
	//
	// The arithmetic was right the whole time. It simply never applied. So the
	// reservation must carry a selector that outranks the utility, and this is
	// the assertion that says so.
	const re = /ion-tabs \.g-page ion-content[^{]*\{[\s\S]*?--padding-bottom:\s*calc/;
	const match = re.exec(css);
	assert.ok(match, "the reservation rule exists");
	assert.match(
		match[0],
		/ion-content\.ion-no-padding/,
		"the reservation must name .ion-no-padding, or Ionic's utility zeroes it and " +
			"every tab screen ends under the bar with the calc() looking perfectly correct",
	);
});

test("the desktop override is just as specific as the rule it undoes", () => {
	// Same trap, mirrored: if the lg: override is less specific than the
	// reservation it cannot switch it off, and every desktop screen keeps 102px
	// of dead scroll below a bar that is not there.
	const lg = /@media \(min-width: 1024px\)\s*\{([\s\S]*?)\n\}/.exec(css);
	assert.ok(lg, "the lg: override exists");
	assert.match(lg[1], /ion-content\.ion-no-padding/, "and matches the reservation's specificity");
});
