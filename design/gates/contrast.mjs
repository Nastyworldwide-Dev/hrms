// Gate 2 — contrast over the spec §14.2 matrix, computed from design/tokens.json.
// Ratios are COMPUTED (WCAG 2.x relative luminance), never copied from the spec
// table; each pair is compared against its required threshold. Glass backgrounds
// are alpha-composited over the app background first. Always enforcing: exit 1
// on any regression, including the §2.4 expected failure flipping to a pass.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const tokens = JSON.parse(readFileSync(join(ROOT, "design", "tokens.json"), "utf8"));

// ---------- colour math ----------

function parse(c) {
	if (typeof c !== "string") throw new Error(`not a colour: ${c}`);
	const hex = c.match(/^#([0-9a-fA-F]{6})$/);
	if (hex) return { rgb: [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)), a: 1 };
	const fn = c.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/);
	if (fn) return { rgb: [+fn[1], +fn[2], +fn[3]], a: fn[4] === undefined ? 1 : +fn[4] };
	throw new Error(`unparseable colour: ${c}`);
}

// src (with alpha) over opaque bg
const over = (src, bg) => src.rgb.map((ch, i) => src.a * ch + (1 - src.a) * bg[i]);

function luminance([r, g, b]) {
	const lin = [r, g, b].map((ch) => {
		const s = ch / 255;
		return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

function ratio(fgRgb, bgRgb) {
	const [l1, l2] = [luminance(fgRgb), luminance(bgRgb)].sort((a, b) => b - a);
	return (l1 + 0.05) / (l2 + 0.05);
}

// ---------- backgrounds per theme ----------

const themedValue = (name, theme) => {
	const t = tokens["color-themed"][name] || tokens["color-semantic"][name];
	if (!t) throw new Error(`unknown themed token: ${name}`);
	return t.value[theme];
};
const constant = (name) => tokens["color-constant"][name].value;

function glassComposite(theme) {
	const bg = parse(themedValue("bg", theme)).rgb;
	return over(parse(themedValue("glass-fill", theme)), bg);
}
// state tints sit on glass: constant colour at given alpha over the glass composite
function tint(name, alpha, theme) {
	return over({ rgb: parse(constant(name)).rgb, a: alpha }, glassComposite(theme));
}

// ---------- the matrix ----------
// bg: "glass" | ["tint", constantName, alpha] | ["const", name]
// thresholds: 4.5 text, 3.0 non-text UI (§14.1). "—" cells in §14.2 are omitted.
const PAIRS = [
	{ fg: "ink", bg: "glass", min: 4.5, themes: ["light", "dark"] },
	{ fg: "ink2", bg: "glass", min: 4.5, themes: ["light", "dark"] },
	{ fg: "ink-muted", bg: "glass", min: 4.5, themes: ["light", "dark"] },
	{ fg: "ink3", bg: "glass", min: 3.0, themes: ["light", "dark"], note: "non-text" },
	{ fg: "accent-ink", bg: "glass", min: 4.5, themes: ["light", "dark"] },
	{ fg: "on-brand", bg: ["const", "brand"], min: 4.5, themes: ["light"], note: "constant pair" },
	{ fg: "danger-ink", bg: "glass", min: 4.5, themes: ["light", "dark"] },
	{ fg: "warn-ink", bg: "glass", min: 4.5, themes: ["light"] },
	{ fg: "leave-ink", bg: ["tint", "leave", 0.26], min: 4.5, themes: ["light"] },
	{ fg: "success-ink", bg: ["tint", "success", 0.2], min: 4.5, themes: ["light", "dark"] },
];
// §14.2's "ink2 over blob edge" pair was skipped in prompt 1.5 because the blob
// was not a token. Phase 4.1 made it one, so it is asserted below (§3.3 block).
const SKIPPED = [];

let failures = 0;
let checked = 0;

for (const p of PAIRS) {
	for (const theme of p.themes) {
		const fg =
			tokens["color-constant"][p.fg] ? parse(constant(p.fg)).rgb : parse(themedValue(p.fg, theme)).rgb;
		const bg =
			p.bg === "glass" ? glassComposite(theme)
			: p.bg[0] === "tint" ? tint(p.bg[1], p.bg[2], theme)
			: parse(constant(p.bg[1])).rgb;
		const r = ratio(fg, bg);
		const ok = r >= p.min;
		checked++;
		if (!ok) failures++;
		console.log(
			`[contrast] ${ok ? "PASS" : "FAIL"} ${theme.padEnd(5)} ${p.fg} on ${
				p.bg === "glass" ? "glass" : Array.isArray(p.bg) ? p.bg.slice(1).join("@") : p.bg
			} = ${r.toFixed(2)} (min ${p.min}${p.note ? ", " + p.note : ""})`
		);
	}
}

// §2.4 expected failure: brand must stay BELOW 3:1 on light glass. If this
// "improves", the token changed and every §2.4 permission needs re-review.
const brandRatio = ratio(parse(constant("brand")).rgb, glassComposite("light"));
if (brandRatio < 3.0) {
	console.log(`[contrast] PASS light brand on glass = ${brandRatio.toFixed(2)} — below 3:1 as §2.4 asserts (expected failure held)`);
} else {
	failures++;
	console.log(`[contrast] FAIL light brand on glass = ${brandRatio.toFixed(2)} — §2.4 expected failure now passes; brand token changed, re-review every §2.4 permission`);
}
checked++;

// ---------- §3.3 blob placement — the substitute for adaptive contrast ----------
//
// CSS cannot re-sample the backdrop the way the OS does, so the spec's control
// is that no blob centre sits inside the content column. This asserts that
// numerically instead of trusting the prose: it reads the same field tokens the
// CSS does, finds the strongest blob alpha that lands inside the column, and
// measures --ink2 and --ink-muted over the composite.

const VIEWPORT = { w: 390, h: 844 }; // §5 reference
const GUTTER = 15; // content column = 100% − 30px

const px = (name) => parseFloat(tokens.field[name].value);

function blobGeometry(id) {
	const size = px(`blob-${id}-size`);
	const r = size / 2;
	const f = tokens.field;
	const cx = f[`blob-${id}-left`] ? px(`blob-${id}-left`) + r : VIEWPORT.w - px(`blob-${id}-right`) - r;
	const cy = f[`blob-${id}-top`] ? px(`blob-${id}-top`) + r : VIEWPORT.h - px(`blob-${id}-bottom`) - r;
	return { cx, cy, r, colour: parse(f[`blob-${id}-color`].value) };
}

// radial-gradient(circle, C, transparent 70%): alpha falls linearly to 0 at 70% of r
const alphaAt = (dist, r, peak) => (dist >= r * 0.7 ? 0 : peak * (1 - dist / (r * 0.7)));

// nearest point of the content column to the blob centre — where the blob is
// strongest *inside* the column, which is the worst case text can sit on
function worstAlphaInColumn(b) {
	const nearestX = Math.min(Math.max(b.cx, GUTTER), VIEWPORT.w - GUTTER);
	const nearestY = Math.min(Math.max(b.cy, 0), VIEWPORT.h);
	const dist = Math.hypot(b.cx - nearestX, b.cy - nearestY);
	return { alpha: alphaAt(dist, b.r, b.colour.a), centreInside: dist === 0 };
}

for (const theme of ["light", "dark"]) {
	const bg = parse(themedValue("bg", theme)).rgb;
	const fieldOpacity = tokens["color-themed"]["blob-opacity"].value[theme];

	for (const id of ["a", "b", "c"]) {
		const b = blobGeometry(id);
		const { alpha, centreInside } = worstAlphaInColumn(b);
		if (alpha <= 0) continue;

		// blob over app bg, then the glass panel over that — text sits on glass
		const overBg = over({ rgb: b.colour.rgb, a: alpha * fieldOpacity }, bg);
		const surface = over(parse(themedValue("glass-fill", theme)), overBg);

		for (const inkName of ["ink2", "ink-muted"]) {
			const r = ratio(parse(themedValue(inkName, theme)).rgb, surface);
			const ok = r >= 4.5;
			checked++;
			if (!ok) failures++;
			console.log(
				`[contrast] ${ok ? "PASS" : "FAIL"} ${theme.padEnd(5)} ${inkName} over blob ${id.toUpperCase()} ` +
					`inside the content column = ${r.toFixed(2)} (min 4.5, §3.3)` +
					(centreInside ? " — CENTRE IS INSIDE THE COLUMN" : "")
			);
		}
	}
}

for (const s of SKIPPED) console.log(`[contrast] SKIP ${s}`);
console.log(`GATE_RESULT ${JSON.stringify({ gate: "contrast", checked, failures, skipped: SKIPPED.length })}`);
process.exit(failures ? 1 : 0);
