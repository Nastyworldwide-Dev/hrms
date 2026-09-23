// Gate 9 — GEOMETRIC SCALE: a 4pt spacing grid and a modular type ramp.
//
// Measured on 22 Sep 2026, before this gate existed:
//   spacing/radius/layout carried 3.5 6 9 11.5 13 14 15 17 18 19 22 30 — 11 of
//   14 spacing and radius values off any grid, five separate type tokens all
//   at 10px, and type steps ranging 1.05 to 1.387.
//
// Why a grid at all. Every screen density in use divides by 4, so an 11.5px
// value lands on a fractional device pixel and rounds differently on each
// phone — the same panel is 1px taller on one handset than another, and no
// amount of eyeballing finds it. Material 3 layout and Apple HIG both build on
// 4/8; so does every design system that ships (Polaris, Carbon, Fluent).
//
// Why a modular ramp. A step the eye cannot resolve does no work: 21.5 next to
// 22 is two names for one size, and a hierarchy nobody can see is decoration.
// A ratio in the 1.125–1.333 band (Tim Brown, modular scale; Material's own
// ramp sits inside it) guarantees every adjacent pair is distinguishable.
//
// Static — reads design/tokens.json only. No site needed.
//
//   node scale.mjs

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const tokens = JSON.parse(readFileSync(join(ROOT, "design", "tokens.json"), "utf8"));

const GRID = 4;

//: Values that are legitimately off the grid, each with the reason. A hairline
//: cannot be 4px, and a reference viewport is a device fact rather than a
//: spacing decision. Anything not listed here must sit on the grid.
const GRID_EXEMPT = {
	"layout.tabbar-border": "a hairline is 1px by definition; 4px is a stripe",
	"layout.viewport-width": "the reference device's real width, not a spacing choice",
	"layout.viewport-height": "the reference device's real height",
	"layout.touch-target-min": "44px is the platform floor (HIG); it is not ours to round",
	"layout.content-column-lg": "720px — signed off by the owner as a measured column width",
};

//: Blur radii are optical, not layout: a grid buys nothing. Excluded as a
//: GROUP, deliberately and visibly. (The background-blob group that used to
//: sit here is gone with the blobs, owner ruling 23 Sep 2026.)
const EXEMPT_GROUPS = new Set(["blur"]);

const offGrid = [];
for (const group of ["spacing", "radius", "layout"]) {
	for (const [name, token] of Object.entries(tokens[group] || {})) {
		if (EXEMPT_GROUPS.has(group)) continue;
		const key = `${group}.${name}`;
		if (key in GRID_EXEMPT) continue;
		const raw = String(token.value ?? token.fallback ?? "");
		for (const m of raw.matchAll(/(-?\d+(?:\.\d+)?)px/g)) {
			const px = Math.abs(Number(m[1]));
			if (px % GRID !== 0) offGrid.push(`  ${key} = ${raw}   (${m[1]}px is not a multiple of ${GRID})`);
		}
	}
}

// ---------- type ramp --------------------------------------------------------
const scale = tokens.type?.scale || {};
const sizes = [];
for (const [name, s] of Object.entries(scale)) {
	const m = String(s.size || "").match(/^(\d+(?:\.\d+)?)px$/);
	if (!m) {
		offGrid.push(`  type.scale.${name} has no px size`);
		continue;
	}
	sizes.push({ name, px: Number(m[1]) });
}

//: Sizes must be whole pixels. A half-pixel type size renders at a different
//: weight on every device pixel ratio — the reason 21.5 and 14.5 existed at all
//: was that nobody was choosing them from a scale.
const fractional = sizes.filter((s) => !Number.isInteger(s.px)).map((s) => `  type.scale.${s.name} = ${s.px}px is not a whole pixel`);

//: Body copy floor. Labels, badges and eyebrows are not body copy and are
//: allowed the ramp's bottom step; anything a sentence is set in is not.
const BODY_ROLES = ["row-label", "card-title", "kra-label", "body", "paragraph"];
const BODY_FLOOR = 14;
const tooSmall = sizes
	.filter((s) => BODY_ROLES.includes(s.name) && s.px < BODY_FLOOR)
	.map((s) => `  type.scale.${s.name} = ${s.px}px — body copy floor is ${BODY_FLOOR}px`);

//: Every distinct size must be a step on ONE ramp, and adjacent steps must be
//: far enough apart to be told apart. Two ROLES may share a step (a stat number
//: and a ring centre are the same size in different weights); what is refused
//: is a ramp with rungs 1.05 apart.
const MIN_RATIO = 1.125;
const MAX_RATIO = 1.334;
//: Roles that are a FITTING problem rather than a reading problem, and are
//: therefore outside the ramp by decision. Each must say so in its own
//: description, so the exception is on the record next to the value.
//:
//: A tab label is the case that forced this: five uppercase words have to fit
//: one 390px bar beside a 20px icon, and moving it onto the ramp's 12px step
//: on 22 Sep 2026 made them overlap into "CALENDARREQUESTS" on every screen.
const RAMP_EXEMPT = new Set(["tab-label"]);
for (const name of RAMP_EXEMPT) {
	const step = scale[name];
	if (!step) continue;
	if (!/outside it|not a step on the/i.test(step.description || "")) {
		offGrid.push(`  type.scale.${name} is ramp-exempt but does not say why in its description`);
	}
}

const distinct = [...new Set(sizes.filter((s) => !RAMP_EXEMPT.has(s.name)).map((s) => s.px))].sort(
	(a, b) => a - b
);
const badSteps = [];
for (let i = 1; i < distinct.length; i++) {
	const ratio = distinct[i] / distinct[i - 1];
	if (ratio < MIN_RATIO || ratio > MAX_RATIO) {
		const who = (px) => sizes.filter((s) => s.px === px).map((s) => s.name).join(", ");
		badSteps.push(
			`  ${distinct[i - 1]}px -> ${distinct[i]}px is ${ratio.toFixed(3)} (want ${MIN_RATIO}-${MAX_RATIO})\n` +
				`      ${distinct[i - 1]}px: ${who(distinct[i - 1])}\n      ${distinct[i]}px: ${who(distinct[i])}`
		);
	}
}

// ---------- the stylesheet, not just the tokens ------------------------------
// A token system on a 4pt grid is worth nothing if the components that consume
// it hand-write 11px beside it. Measured 22 Sep 2026 before the density pass:
// 96 off-grid declarations in glass-components.css — gaps of 9, 11 and 13, row
// padding of 13x14, a 27px icon well, a 66px header.
//
// 1, 2 and 3px are exempt and always will be: a hairline, a rim and a focus
// ring are not spacing, and rounding them changes what they are.
const HAIRLINES = new Set([1, 2, 3]);
const CSS_PROPS = new Set([
	"gap", "padding", "margin", "min-height", "height", "width",
	"top", "bottom", "left", "right", "inset", "border-radius",
]);
//: Values a component is allowed to hold off-grid, each with its reason.
const CSS_EXEMPT = new Map([
	[2.5, "the notification dot's rim curve — a 4px radius on a 5px dot is a square"],
]);

const cssPath = join(ROOT, "frontend/src/theme/glass-components.css");
const cssRaw = readFileSync(cssPath, "utf8");
// Comments are BLANKED, not stripped: a comment explaining "this was 11px"
// must not be counted as an 11px declaration. Six separate gates in this repo
// have been caught by their own prose; this one is written knowing that.
const cssBody = cssRaw
	.split(/(\/\*[\s\S]*?\*\/)/)
	.filter((part) => !part.startsWith("/*"))
	.join("");

const cssOffGrid = [];
for (const m of cssBody.matchAll(/([a-z-]+):([^;{}]+);/g)) {
	if (!CSS_PROPS.has(m[1])) continue;
	for (const n of m[2].matchAll(/(-?\d+(?:\.\d+)?)px/g)) {
		const px = Math.abs(Number(n[1]));
		if (!px || px % GRID === 0 || HAIRLINES.has(px) || CSS_EXEMPT.has(px)) continue;
		cssOffGrid.push(`  glass-components.css: ${m[1]}: ${m[2].trim()}   (${n[1]}px)`);
	}
}

const problems = [
	["off the 4pt grid", offGrid],
	["fractional type sizes", fractional],
	["body copy below the floor", tooSmall],
	["type steps outside the ratio band", badSteps],
	["off the 4pt grid in the stylesheet", cssOffGrid],
].filter(([, list]) => list.length);

for (const [what, list] of problems) {
	console.log(`[scale] ${list.length} ${what}:`);
	for (const line of list) console.log(line);
}

if (problems.length) {
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "scale", status: "fail", offGrid: offGrid.length + cssOffGrid.length, steps: badSteps.length })}`);
	process.exit(1);
}

console.log(
	`[scale] OK — ${Object.keys(tokens.spacing).length + Object.keys(tokens.radius).length} spacing/radius values on a ${GRID}pt grid, ` +
		`${distinct.length} type steps, ratios ${distinct.length > 1 ? (distinct[1] / distinct[0]).toFixed(2) : "n/a"}-${distinct.length > 1 ? (distinct[distinct.length - 1] / distinct[distinct.length - 2]).toFixed(2) : "n/a"}`
);
console.log(`GATE_RESULT ${JSON.stringify({ gate: "scale", status: "ok", steps: distinct.length })}`);
process.exit(0);
