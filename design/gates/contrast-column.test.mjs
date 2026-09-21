// The lg: contrast proof must be computed from the SAME content-column width
// the app ships, not from a literal copied into the gate.
//
// contrast.mjs:188 read `column: 720` while --g-content-column-lg lived in
// tokens.json. tokens.json describes that value as "a starting value, expected
// to be tuned once on device — which is why the spec insists it be a single
// token", so the one edit it exists to receive is exactly the edit its proof
// could not see. Widening it to 880 makes the column reach blob B at 1024px
// dark (ink-muted 4.31:1, under the 4.5 floor); with the literal in place the
// gate stays green and reports the old geometry.
//
// This is a grep-shaped test on purpose. Asserting the number would pass the
// moment someone edits the literal to match, which is the defect.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(HERE, "contrast.mjs"), "utf8");
const tokens = JSON.parse(readFileSync(join(HERE, "..", "tokens.json"), "utf8"));

test("the lg: content column is read from tokens.json, not hardcoded", () => {
	const hardcoded = /column:\s*\d+/.exec(src);
	assert.equal(
		hardcoded,
		null,
		`contrast.mjs hardcodes ${hardcoded?.[0]}; it must read ` +
			"tokens.layout['content-column-lg'] so tuning the token re-proves the geometry",
	);
	assert.match(src, /content-column-lg/);
});

test("the token the gate depends on still exists and is a px length", () => {
	const v = tokens.layout?.["content-column-lg"]?.value;
	assert.ok(v, "tokens.layout['content-column-lg'] is missing");
	assert.match(v, /^\d+px$/, `expected a px length, got ${v}`);
});

// The same class, found by reviewing the fix above rather than by the fix
// itself: `column` was not the only literal in this gate duplicating a token.
// Two lines under it sat `gutter: 15`, and twenty lines up `VIEWPORT = {w:390,
// h:844}` and `GUTTER = 15` — all four are tokens (spacing.screen-gutter,
// layout.viewport-width, layout.viewport-height). The commit that fixed
// `column` claimed "this was the one literal". It was not; it was the one I
// happened to be looking at.
//
// Each is asserted by NAME rather than by value, for the reason above: an
// assertion on 15 passes the moment someone edits the token to 16 and copies
// 16 into the gate, which is the defect restated.

const LITERAL_TOKENS = [
	{ literal: /const\s+GUTTER\s*=\s*\d/, token: "spacing.screen-gutter", reads: /screen-gutter/ },
	{ literal: /\bgutter:\s*\d/, token: "spacing.screen-gutter", reads: /screen-gutter/ },
	{ literal: /\bw:\s*\d{3}/, token: "layout.viewport-width", reads: /viewport-width/ },
	{ literal: /\bh:\s*\d{3}/, token: "layout.viewport-height", reads: /viewport-height/ },
];

test("no geometry literal in the gate duplicates a token it could read", () => {
	for (const { literal, token, reads } of LITERAL_TOKENS) {
		const hit = literal.exec(src);
		assert.equal(hit, null, `contrast.mjs hardcodes ${hit?.[0]}; read ${token} instead`);
		assert.match(src, reads, `expected contrast.mjs to read ${token}`);
	}
});

test("every token the gate's geometry depends on exists and is a px length", () => {
	const need = [
		["spacing", "screen-gutter"],
		["layout", "viewport-width"],
		["layout", "viewport-height"],
	];
	for (const [group, name] of need) {
		const v = tokens[group]?.[name]?.value;
		assert.ok(v, `tokens.${group}['${name}'] is missing`);
		assert.match(v, /^\d+px$/, `expected a px length for ${group}.${name}, got ${v}`);
	}
});

// px() must refuse a value parseFloat would truncate into a plausible number.
// `calc(100% - 30px)` reads as 100 — a geometry input wrong by 85px that still
// prints PASS. layout.content-column IS a calc() today, so this is one
// mis-pointed lookup away, not hypothetical.
//
// The regex is lifted OUT of contrast.mjs rather than retyped here: a copy
// would drift from the thing it claims to test, which is the defect this whole
// file exists to catch.
test("px() validates its token value against an exact px length", () => {
	// `[^/]+` stops at the first forward slash, so this capture assumes the px
	// pattern contains no escaped `/`. It does not today (digits, dot, minus,
	// "px"); if one is ever added, this stops matching and the assert below
	// fails loudly rather than silently testing a truncated regex.
	const m = /!(\/\^-\?[^/]+\/)\.test\(raw\)/.exec(src);
	assert.ok(m, "contrast.mjs px() must test `raw` against a px-length regex before parseFloat");
	const re = new RegExp(m[1].slice(1, -1));

	// values parseFloat would turn into a plausible wrong number
	for (const v of ["calc(100% - 30px)", "1rem", "12", "100%", "auto", ""])
		assert.equal(re.test(v), false, `px() must reject ${JSON.stringify(v)}`);

	// shapes real tokens use, including the negative offsets the field blobs
	// are positioned with — blob-b-right is -163px, and dropping that minus is
	// exactly how this geometry was misread once already
	for (const v of ["15px", "-163px", "844px", "0px", "1.5px"])
		assert.equal(re.test(v), true, `px() must accept ${v}`);
});

// The guard added above only protects the reads that GO THROUGH px(). Three
// did not: `column: parseFloat(tokens.layout["content-column-lg"].value)` and
// the two blob reads in the lg: block. So the commit that added validation
// left unvalidated the very token whose copied literal started this whole
// chain — a guard is only as wide as its call sites.
//
// Asserting the ABSENCE of the unguarded form, not the presence of the guarded
// one: a test that checks `px("layout", "content-column-lg")` appears would
// stay green while a fourth raw parseFloat is added next to it.
test("parseFloat is called in exactly one place — inside px(), after validation", () => {
	// comments talk ABOUT parseFloat; only real calls count
	const code = src.replace(/^\s*\/\/.*$/gm, "");
	const calls = [...code.matchAll(/parseFloat\(([^)]*)\)/g)].map((m) => m[1].trim());
	assert.deepEqual(
		calls,
		["raw"],
		"every geometry read must go through px()/fieldPx(); found raw parseFloat call(s) on: " +
			calls.filter((c) => c !== "raw").join(", "),
	);
});

// Fifth instance of the class, and the first one that is not a token at all.
//
// LG.scale in contrast.mjs says `{ a: 0.32, b: 0.29, c: 0.25 }` with the
// comment "matching glass-components.css". That file is HAND-AUTHORED (its own
// header says so) and holds `width: 32vw` / `29vw` / `25vw` as literals under
// @media (min-width: 1024px). So the gate keeps a copy of a number that has no
// token behind it: edit the CSS and the lg: proof goes on proving the old
// geometry, green. Exactly 59e20f697's defect, one layer further out.
//
// The offsets are a subtler version. The gate does NOT copy them — it derives
// each from the mobile tokens as (offset/size)*scale, because glass-components
// .css holds "the origin:size ratio solved for mobile". That derivation lands
// within 0.003vw of the CSS's own -25.04/-22.51/-19.03vw. That agreement is
// the whole basis for the lg: proof being about the shipped app rather than
// about a model of it, and nothing was checking it.
//
// So this asserts the gate's MODEL against the CSS's DECLARATION, in both
// halves. Tolerance is 0.005vw: the CSS rounds to 2dp, the derivation does not.
const css = readFileSync(
	join(HERE, "..", "..", "frontend", "src", "theme", "glass-components.css"),
	"utf8",
);

test("the lg: blob model matches what glass-components.css actually declares", () => {
	const lgBlock = /@media\s*\(min-width:\s*1024px\)\s*\{([\s\S]*?)\n\}/g;
	const blocks = [...css.matchAll(lgBlock)].map((m) => m[1]).join("\n");
	assert.ok(blocks, "no @media (min-width: 1024px) block found in glass-components.css");

	const scale = /scale:\s*\{([^}]*)\}/.exec(src);
	assert.ok(scale, "contrast.mjs must declare LG.scale");

	for (const id of ["a", "b", "c"]) {
		const rule = new RegExp(`\\.g-lightfield__blob--${id}\\s*\\{([^}]*)\\}`).exec(blocks);
		assert.ok(rule, `glass-components.css has no lg: rule for blob ${id}`);

		// width: the gate's scale must equal the CSS's vw
		const cssVw = /width:\s*([\d.]+)vw/.exec(rule[1]);
		assert.ok(cssVw, `blob ${id} lg: rule declares no vw width`);
		const gateScale = new RegExp(`\\b${id}:\\s*([\\d.]+)`).exec(scale[1]);
		assert.ok(gateScale, `LG.scale has no entry for blob ${id}`);
		// a tolerance, not equality: 0.29 * 100 is 28.999999999999996 in binary
		// floating point, and this assertion is about the app's geometry, not
		// about IEEE 754. 1e-9 is far below any real CSS edit.
		assert.ok(
			Math.abs(Number(gateScale[1]) * 100 - Number(cssVw[1])) < 1e-9,
			`LG.scale.${id} says ${gateScale[1]} but glass-components.css ships ${cssVw[1]}vw`,
		);

		// offset: the gate derives it from the mobile tokens; the CSS states it
		const side = tokens.field[`blob-${id}-left`] ? "left" : "right";
		const cssOff = new RegExp(`${side}:\\s*(-?[\\d.]+)vw`).exec(rule[1]);
		assert.ok(cssOff, `blob ${id} lg: rule declares no ${side} offset in vw`);
		const mobileOffset = parseFloat(tokens.field[`blob-${id}-${side}`].value);
		const mobileSize = parseFloat(tokens.field[`blob-${id}-size`].value);
		const derived = (mobileOffset / mobileSize) * Number(gateScale[1]) * 100;
		assert.ok(
			Math.abs(derived - Number(cssOff[1])) < 0.005,
			`blob ${id}: the gate derives ${derived.toFixed(3)}vw from the mobile tokens, ` +
				`glass-components.css ships ${cssOff[1]}vw. The lg: proof models a blob the app does not draw.`,
		);
	}
});
