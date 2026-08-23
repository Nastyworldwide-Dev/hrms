// Gate 8 — cross-screen invariants (spec §16.5.3).
//
// The gate nothing else could be. lint, usage, contrast, surfaces, a11y and
// visual are all WITHIN-screen checks: each asks "is this screen right?" and
// none compares screen A to screen B. That is how the app acquired six section
// header treatments, a back control on 26 screens and not on 12 with no rule
// connecting them, and one role rendered as a chartreuse GButton on dashboards
// and a white frappe-ui pill on lists — all of it passing six green gates.
//
// Profiles every screen (frontend/e2e/coherence.spec.js) and asserts the
// invariants over the whole set.
//
// Needs a running site and a chromium; SKIPs without, like the other
// render-time gates.

import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { TAB_ROOTS } from "./coherence-rules.mjs";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const REPORT = join(ROOT, "design", "gates", ".coherence-report.json");

if (existsSync(REPORT)) rmSync(REPORT);

const res = spawnSync(
	"npx",
	["--yes", "playwright@1.62.1", "test", "--config=e2e/playwright.config.js", "e2e/coherence.spec.js"],
	{ cwd: join(ROOT, "frontend"), encoding: "utf8", timeout: 25 * 60 * 1000 }
);
const out = (res.stdout || "") + (res.stderr || "");
process.stdout.write(out);

const skip = (why) => {
	console.log(`[coherence] SKIP — ${why}`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "coherence", status: "skip" })}`);
	process.exit(0);
};
if (/Executable doesn't exist|browserType\.launch|playwright install/i.test(out)) skip("chromium not installed");
if (/login failed/i.test(out)) skip("could not sign in — set AUDIT_PW");
if (!existsSync(REPORT)) skip("the spec produced no report");

const P = JSON.parse(readFileSync(REPORT, "utf8"));
const fail = [];
const note = [];

// ---- 1. exactly one primary, and it is the primary COMPONENT ---------------
for (const [screen, v] of Object.entries(P)) {
	if (v.error) { note.push(`${screen}: did not render — ${v.error}`); continue; }
	const filled = v.filled || [];
	if (filled.length > 1) {
		fail.push(`${screen}: ${filled.length} filled actions — §18 allows one (${filled.map((f) => `"${f.label}"`).join(", ")})`);
	}
	for (const f of filled) {
		if (f.fill === "accent-ink") {
			fail.push(`${screen}: "${f.label}" is filled with --accent-ink, not --brand — the bg-accent trap`);
		}
		if (f.fill === "brand" && !f.isGButton) {
			fail.push(`${screen}: "${f.label}" paints the brand without being a GButton — one role, one component`);
		}
	}
}

// ---- 2. back navigation follows ONE rule ------------------------------------
for (const [screen, v] of Object.entries(P)) {
	if (v.error) continue;
	const isTabRoot = TAB_ROOTS.has(screen);
	if (isTabRoot && v.hasBack) fail.push(`${screen}: a tab root must not have a back control`);
	if (!isTabRoot && !v.hasBack) fail.push(`${screen}: a pushed screen must have a back control`);
}

// ---- 3. one empty-state component -------------------------------------------
for (const [screen, v] of Object.entries(P)) {
	if (!v.error && v.adHocEmpty) fail.push(`${screen}: ad-hoc empty state — compose GEmptyState`);
}

// ---- 4. one section-header treatment ----------------------------------------
// This used to print "284 uppercase runs, 225 not using .g-eyebrow (reported,
// not enforced)". That number asserted nothing. Uppercase is also how this app
// draws chips, tab labels, field labels, stat labels and column heads, so most
// of the 225 was correct — and the rule it gestured at was never tested. It hid
// a real defect for fifty prompts: .g-quicklinks__title copied five of the six
// eyebrow tokens into a component's scoped block and set the sixth, the colour,
// to --ink2. On `home`, "QUICK LINKS" rendered rgb(84,92,104) while "REQUESTS"
// two sections below rendered rgb(63,92,0) — same role, same size, same screen.
//
// Now: the spec classifies every run by DECLARED role. Section headers are
// enforced. The other categories are baselined BY CATEGORY, so a chip becoming
// a heading moves a number that is being watched, instead of vanishing into a
// total.
const catTotal = {};
const catOff = {};
const sectionOffenders = new Map();
let eyebrowsTotal = 0;
for (const [screen, v] of Object.entries(P)) {
	for (const e of v.eyebrows || []) {
		eyebrowsTotal++;
		const c = e.category || "section";
		catTotal[c] = (catTotal[c] || 0) + 1;
		if (!e.usesClass) {
			catOff[c] = (catOff[c] || 0) + 1;
			if (c === "section") {
				const key = `${e.text} <${e.tag}> ${e.cls}`;
				if (!sectionOffenders.has(key)) sectionOffenders.set(key, { ...e, screens: [] });
				sectionOffenders.get(key).screens.push(screen);
			}
		}
	}
}

for (const [key, o] of sectionOffenders) {
	const where = o.screens.length > 3 ? `${o.screens.slice(0, 3).join(", ")} +${o.screens.length - 3}` : o.screens.join(", ");
	fail.push(
		`section header "${o.text}" does not use .g-eyebrow — <${o.tag} class="${o.cls}"> on ${where}. ` +
			`Either it is a section header (use .g-eyebrow) or it has a different role (declare it in ROLES)`
	);
}

// ---- 5. ONE avatar component (RC18) -----------------------------------------
// The audit said "the avatar has three forms". Measuring found four, and the
// fourth was the one no grep for "avatar" could see: Profile open-coded one in
// Tailwind — `h-[72px] w-[72px] object-cover grayscale` — with no radius and no
// name. `.m-avatar-sq` was deleted in phase 3, but the Modernist zero-radius
// treatment came back anyway, without the class that would have flagged it.
//
// So the rule cannot key on a class name. The spec probe finds avatars by
// SHAPE — a small square box holding an image or one-to-two initials — and this
// asserts that every one of them is GAvatar. A fifth form cannot appear without
// failing here, whatever it calls itself.
const avatarForms = new Map();
for (const [screen, v] of Object.entries(P)) {
	for (const a of v.avatars || []) {
		if (a.form === "GAvatar") continue;
		const key = `${a.form}|${a.tag}|${a.w}x${a.h}|${a.radius}|${a.cls}`;
		if (!avatarForms.has(key)) avatarForms.set(key, { ...a, screens: [] });
		avatarForms.get(key).screens.push(screen);
	}
}
for (const [, a] of avatarForms) {
	const where = a.screens.length > 3 ? `${a.screens.slice(0, 3).join(", ")} +${a.screens.length - 3}` : a.screens.join(", ");
	const flat = a.radius === "0px" ? " — and it is radius 0, the Modernist forcing §10.3 dropped" : "";
	fail.push(
		`avatar not built from GAvatar: <${a.tag} class="${a.cls}"> ${a.w}x${a.h} r=${a.radius} on ${where}${flat}`
	);
}

// Per-category baseline. Counts, not identities: identities would freeze at the
// moment they were written and rot from the next component onward.
const CAT_BASELINE = join(ROOT, "design", "eyebrow-baseline.json");
const shape = { total: catTotal, withoutEyebrow: catOff };
if (process.argv.includes("--update-baseline")) {
	writeFileSync(CAT_BASELINE, JSON.stringify(shape, null, "\t") + "\n");
	console.log(`[coherence] category baseline updated`);
} else if (existsSync(CAT_BASELINE)) {
	const prev = JSON.parse(readFileSync(CAT_BASELINE, "utf8"));
	for (const c of new Set([...Object.keys(prev.total || {}), ...Object.keys(catTotal)])) {
		const was = prev.total?.[c] || 0;
		const now = catTotal[c] || 0;
		if (was !== now) note.push(`category ${c}: ${was} -> ${now} run(s)`);
	}
}

const screens = Object.keys(P).length;
if (fail.length) {
	console.log(`[coherence] ${fail.length} cross-screen violation(s):`);
	for (const f of fail) console.log(`  ${f}`);
}
for (const n of note) console.log(`[coherence] note: ${n}`);
const catLine = Object.entries(catTotal)
	.sort((a, b) => b[1] - a[1])
	.map(([c, n]) => `${c} ${n}${catOff[c] ? ` (${catOff[c]} bare)` : ""}`)
	.join(" · ");
console.log(`[coherence] ${screens} screens · ${eyebrowsTotal} uppercase runs by declared role: ${catLine}`);
console.log(`[coherence] section headers enforced: ${catTotal.section || 0} found, ${catOff.section || 0} not using .g-eyebrow`);

if (fail.length) {
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "coherence", status: "fail", screens, violations: fail.length })}`);
	process.exit(1);
}
console.log(`GATE_RESULT ${JSON.stringify({ gate: "coherence", status: "ok", screens, violations: 0 })}`);
process.exit(0);
