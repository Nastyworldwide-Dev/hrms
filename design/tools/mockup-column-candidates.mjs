// Evidence for the open desktop-column ruling (plan 16 Sep §3 O2, and owner
// questions 2 and 3).
//
// mockup-4 declares --g-content-column-lg: 880px. The shipped token is 720px
// and tokens.json calls it "a starting value, expected to be tuned once on
// device". contrast.mjs's §20.4 block already models the lg: field geometry,
// so the question "is 880 adoptable?" is measurable rather than a taste call:
// widening the column moves it toward blob B, and blob B is the one the model
// can reach.
//
// Run: node design/tools/mockup-column-candidates.mjs   (from the repo root)
//
// Findings, 22 Sep 2026 — THREE models, and the disagreement IS the finding.
// Corrected after an adversarial check refuted the first version of it.
//
// MODEL 1 — the gate as written (§20.4). The column is LEFT-ALIGNED at
// nav + gutter, and the blobs are anchored to the VIEWPORT. Under it 880px
// FAILS: at 1024px with the nav expanded to 216px, dark --ink-muted over blob
// B measures 4.31:1 against the repo's 4.5 floor, and
// `node design/gates/contrast.mjs` exits 1. 720px clears all 24 combinations
// with ZERO alpha. 773px is the widest value that still clears the floor —
// NOT 800px, as an earlier draft of this header said. Above ~778 the number
// stops moving because the column is viewport-clamped.
//
// MODEL 2 — the geometry the app actually draws for its capped views. All 15
// files that use max-w-content-column-lg pair it with mx-auto; none is
// left-aligned. So the column is CENTRED in the space beside the nav, with
// lg:p-7 (28px, Tailwind default — the glass spacing scale only ADDS five
// named keys) insetting the text further. AND the field is not
// viewport-anchored: GLightField mounts inside <ion-page> (GPage.vue:26) and
// .g-lightfield is `position:absolute; inset:0`, so in TabbedView's flex shell
// the blob box starts at x=nav while the blob offsets are still in vw. The
// gate misses that shift. Browser-measured at 1024/nav216: blob A's real
// centre is x=+123, not the gate's -93.
// Under the corrected geometry the capped views are clear at BOTH widths, but
// not by the same margin: at 1024/nav216, 720px clears the nearest blob's
// reach by 50px and 880px by only 6px.
//
// MODEL 3 — and this is the one that matters. One shipped lg: container is
// UNCAPPED: frontend/src/views/expense_claim/Dashboard.vue is
// `lg:grid lg:grid-cols-[1fr_1.2fr] lg:p-7` with no max-width, inside
// BaseLayout's `lg:max-w-none lg:mx-0`. There the blobs DO reach the text box:
// browser-measured alpha 0.019-0.032 at 1440px and 0.060-0.089 at 1920px,
// which puts dark --ink-muted at 4.42 and 4.07 against the 4.5 floor. The gate
// prints all 24 lg: combinations as "ZERO alpha" clear. So the gate is not
// merely pessimistic about wide columns — it is OPTIMISTIC about this one, in
// the direction that hides a real sub-AA combination.
// This probe's arithmetic is slightly CONSERVATIVE against the browser: it
// derives the offsets from the token ratio, the browser resolves the vw
// lengths directly, and the browser reads higher alphas (0.019/0.023/0.032 at
// 1440 vs this probe's 0.014/0.012/0.021). Where they differ the browser is
// authoritative; both agree on which cells fail and in which direction.
// The exposed call site is `.g-chip--muted` (glass-components.css:755):
// `background: transparent` with `color: var(--g-ink-muted)`, and its own
// recorded margin is 4.56/4.58. It has ~0.06 of headroom, so ANY blob alpha
// takes it under.
//
// What this means for the owner's question on 880px: it is not adoptable
// today, because adopting it turns a green enforcing gate red and that is a
// real CI failure. But the gate's lg: model needs its own fix — wrong column
// alignment AND wrong blob anchoring — and fixing it surfaces a defect the
// column question never had anything to do with.
//
// Also: mockup-4 carries four token divergences, and two of them (glass-fill
// dark, content-column-lg) break a gate the shipped tokens pass. Blanket
// sign-off would adopt both.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const tokens = JSON.parse(readFileSync(join(ROOT, "design", "tokens.json"), "utf8"));

// Same math as design/gates/contrast.mjs. Copied deliberately and stated as a
// copy: contrast.mjs has no exports and process.exit()s at module scope, so it
// cannot be imported. If the gate's formulas change, this probe's header
// findings are stale and must be re-run, not trusted.
function parse(c) {
	const hex = c.match(/^#([0-9a-fA-F]{6})$/);
	if (hex) return { rgb: [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)), a: 1 };
	const fn = c.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/);
	if (fn) return { rgb: [+fn[1], +fn[2], +fn[3]], a: fn[4] === undefined ? 1 : +fn[4] };
	throw new Error(`unparseable colour: ${c}`);
}
const over = (src, bg) => src.rgb.map((ch, i) => src.a * ch + (1 - src.a) * bg[i]);
const luminance = ([r, g, b]) => {
	const lin = [r, g, b].map((ch) => {
		const s = ch / 255;
		return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
};
const ratio = (f, b) => {
	const [l1, l2] = [luminance(f), luminance(b)].sort((a, b2) => b2 - a);
	return (l1 + 0.05) / (l2 + 0.05);
};
const themed = (name, theme) => (tokens["color-themed"][name] || tokens["color-semantic"][name]).value[theme];
const px = (group, name) => {
	const raw = tokens[group]?.[name]?.value;
	if (!/^-?\d+(\.\d+)?px$/.test(raw)) throw new Error(`tokens.${group}["${name}"] = "${raw}" is not a px length`);
	return parseFloat(raw);
};

const GUTTER = px("spacing", "screen-gutter");
const SCALE = { a: 0.32, b: 0.29, c: 0.25 }; // §20.4, as contrast.mjs holds it
const NAV = [72, 216];
const VIEWPORTS = [1024, 1280, 1440, 1920];
const CANDIDATES = [720, 773, 774, 800, 880]; // shipped, the gate's ceiling, first fail, round, mockup-4

for (const column of CANDIDATES) {
	let clear = 0;
	const fails = [];
	let worst = { r: Infinity };

	for (const vw of VIEWPORTS) {
		for (const nav of NAV) {
			const colStart = nav + GUTTER;
			const colEnd = Math.min(colStart + column, vw - GUTTER);

			for (const id of ["a", "b", "c"]) {
				const size = vw * SCALE[id];
				const r = size / 2;
				const f = tokens.field;
				const isLeft = Boolean(f[`blob-${id}-left`]);
				const mobileSize = px("field", `blob-${id}-size`);
				const mobileOffset = px("field", `blob-${id}-${isLeft ? "left" : "right"}`);
				const offset = (mobileOffset / mobileSize) * size;
				const cx = isLeft ? offset + r : vw - offset - r;

				const nearest = Math.min(Math.max(cx, colStart), colEnd);
				const dist = Math.abs(cx - nearest);
				const alpha = dist >= r * 0.7 ? 0 : parse(f[`blob-${id}-color`].value).a * (1 - dist / (r * 0.7));
				if (alpha <= 0) {
					clear++;
					continue;
				}

				for (const theme of ["light", "dark"]) {
					const bg = parse(themed("bg", theme)).rgb;
					const op = tokens["color-themed"]["blob-opacity"].value[theme];
					const colour = parse(f[`blob-${id}-color`].value);
					const surface = over(parse(themed("glass-fill", theme)), over({ rgb: colour.rgb, a: alpha * op }, bg));
					for (const ink of ["ink2", "ink-muted"]) {
						const r2 = ratio(parse(themed(ink, theme)).rgb, surface);
						if (r2 < worst.r) worst = { r: r2, where: `${vw}px nav:${nav} ${theme} ${ink} blob ${id.toUpperCase()}` };
						if (r2 < 4.5) fails.push(`${vw}px nav:${nav} ${theme} ${ink} over blob ${id.toUpperCase()} = ${r2.toFixed(2)}`);
					}
				}
			}
		}
	}

	const shipped = column === px("layout", "content-column-lg") ? "  <- SHIPPED" : "";
	const mockup = column === 880 ? "  <- MOCKUP 4" : "";
	console.log(
		`\n${column}px: ${clear}/24 combinations reach the column with ZERO alpha, ${fails.length} below 4.5${shipped}${mockup}`
	);
	if (fails.length) for (const f of fails) console.log(`  FAIL ${f}`);
	else console.log(`  PASS — nothing below the 4.5 floor (worst modelled: ${worst.r === Infinity ? "no overlap at all" : worst.r.toFixed(2)})`);
}

console.log("\nThe gate's floor is 4.5 for ink2 and ink-muted over a blob (§3.3/§20.4).");
console.log("A column that fails here fails `node design/gates/contrast.mjs`, which exits 1.");

// ---------- MODEL 2/3: the geometry the app draws ----------
//
// Two corrections to the gate's model, both browser-verified:
//   1. the column is CENTRED (15/15 max-w-content-column-lg uses have mx-auto)
//      and the text is inset by lg:p-7 = 28px;
//   2. the blob box is the PAGE PANE, which starts at x = nav, while the blob
//      offsets stay in vw — so every left-anchored blob shifts right by nav.
// Plus the case the gate cannot see at all: an uncapped full-width lg view.
const PAD = 28; // lg:p-7, Tailwind default 1.75rem

function realBlob(id, vw, nav) {
	const size = vw * SCALE[id];
	const r = size / 2;
	const f = tokens.field;
	const isLeft = Boolean(f[`blob-${id}-left`]);
	const offset = (px("field", `blob-${id}-${isLeft ? "left" : "right"}`) / px("field", `blob-${id}-size`)) * size;
	// the pane is (vw - nav) wide and starts at x = nav
	const paneW = vw - nav;
	const cx = nav + (isLeft ? offset + r : paneW - offset - r);
	return { cx, r, reach: r * 0.7, colour: parse(f[`blob-${id}-color`].value) };
}

function report(label, boxFor) {
	console.log(`\n${label}`);
	for (const vw of VIEWPORTS) {
		for (const nav of NAV) {
			const box = boxFor(vw, nav);
			const worst = [];
			for (const id of ["a", "b", "c"]) {
				const b = realBlob(id, vw, nav);
				const nearest = Math.min(Math.max(b.cx, box.l), box.r);
				const dist = Math.abs(b.cx - nearest);
				if (dist >= b.reach) {
					worst.push(`${id.toUpperCase()} clear+${Math.round(dist - b.reach)}`);
					continue;
				}
				const alpha = b.colour.a * (1 - dist / b.reach);
				let line = `${id.toUpperCase()} a=${alpha.toFixed(3)}`;
				for (const theme of ["light", "dark"]) {
					const bg = parse(themed("bg", theme)).rgb;
					const op = tokens["color-themed"]["blob-opacity"].value[theme];
					const surface = over(parse(themed("glass-fill", theme)), over({ rgb: b.colour.rgb, a: alpha * op }, bg));
					const r2 = ratio(parse(themed("ink-muted", theme)).rgb, surface);
					line += ` ${theme[0]}:${r2.toFixed(2)}${r2 < 4.5 ? "!FAIL" : ""}`;
				}
				worst.push(line);
			}
			console.log(`  ${vw}px nav:${nav} text [${Math.round(box.l)},${Math.round(box.r)}]  ${worst.join("  |  ")}`);
		}
	}
}

console.log("\n\n========== MODEL 2/3: real geometry (centred column, page-anchored blobs) ==========");
console.log("ink-muted over the worst blob. l:=light d:=dark. !FAIL is below the 4.5 floor.");

for (const column of [720, 880]) {
	report(`--- capped column, max-w-content-column-lg = ${column}px, mx-auto + lg:p-7 ---`, (vw, nav) => {
		const avail = vw - nav;
		const colW = Math.min(column, avail);
		const colLeft = nav + (avail - colW) / 2;
		return { l: colLeft + PAD, r: colLeft + colW - PAD };
	});
}

report(
	"--- UNCAPPED full-width lg view (frontend/src/views/expense_claim/Dashboard.vue) ---",
	(vw, nav) => ({ l: nav + PAD, r: vw - PAD })
);

console.log("\nMODEL 1 is what CI enforces. MODEL 2/3 is what the app draws.");
console.log("The capped views are clear at both widths. The UNCAPPED view is not,");
console.log("and the gate reports it as clear. The exposed call site is");
console.log(".g-chip--muted (transparent background, ink-muted, 4.56/4.58 recorded).");
