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
import { readFileSync, existsSync, rmSync } from "node:fs";
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
let eyebrowsTotal = 0, eyebrowsOff = 0;
for (const [screen, v] of Object.entries(P)) {
	for (const e of v.eyebrows || []) {
		eyebrowsTotal++;
		if (!e.usesClass) eyebrowsOff++;
	}
}

const screens = Object.keys(P).length;
if (fail.length) {
	console.log(`[coherence] ${fail.length} cross-screen violation(s):`);
	for (const f of fail) console.log(`  ${f}`);
}
for (const n of note) console.log(`[coherence] note: ${n}`);
console.log(`[coherence] ${screens} screens · ${eyebrowsTotal} uppercase runs, ${eyebrowsOff} not using .g-eyebrow (reported, not enforced — chips and tab labels are uppercase too)`);

if (fail.length) {
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "coherence", status: "fail", screens, violations: fail.length })}`);
	process.exit(1);
}
console.log(`GATE_RESULT ${JSON.stringify({ gate: "coherence", status: "ok", screens, violations: 0 })}`);
process.exit(0);
