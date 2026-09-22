// Gate 5 — component-usage discipline: "screens compose primitives only".
// Until now that rule lived in CLAUDE.md and nothing enforced it. Phase 5
// writes 41 screens; this is what makes the rule real before then, not after.
//
// Scans frontend/src/views/** and frontend/src/components/** (EXCLUDING
// components/glass/**, which is where the primitives are allowed to live) for:
//   glass-class   — .g-glass / .g-glass-ghost / g-* component classes used
//                   directly instead of the G* component that owns them
//   hand-panel    — a bare element carrying a Glass radius plus a background:
//                   a panel rebuilt by hand where a G* component exists
//   direct-import — importing theme/glass-components.css instead of relying
//                   on the single import in main.js
//
// Same baseline mechanism as the lint gate: design/usage-baseline.json records
// what exists today, NEW violations fail. Currently the baseline absorbs
// everything, so the gate reports without failing.
//   node usage.mjs                    report; exit 1 only on new violations
//   node usage.mjs --strict           exit 1 on any violation (phase 5 mode)
//   node usage.mjs --update-baseline  rewrite the baseline to current counts

import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SRC = join(ROOT, "frontend", "src");
const BASELINE_PATH = join(ROOT, "design", "usage-baseline.json");
// Views are STRICT by default as of phase 4.4: their baseline is zero and
// phase 5 writes 41 screens through this gate. Anywhere else (shared
// components mid-migration) keeps the baseline mechanism, so existing
// exemptions stand. --strict escalates everything.
const STRICT = process.argv.includes("--strict");
const isView = (rel) => rel.startsWith("views/");
const UPDATE = process.argv.includes("--update-baseline");

const SCAN = ["views", "components"];
// the primitives themselves, and the specimen that must render every one of
// them directly, are exempt by definition
// A test that ENFORCES these rules has to name the classes it forbids, so
// scanning it counts the guard as the thing it guards against. Tests ship no
// markup to a browser — nothing in __tests__ can rebuild a panel — so the
// directory is exempt for the same reason components/glass/ is: it is not a
// screen. Narrow on purpose: __tests__ only, not any file with "test" in it.
const EXEMPT = (rel) =>
	rel.startsWith("components/glass/") ||
	rel === "views/DesignSpecimen.vue" ||
	rel.split("/").includes("__tests__");

function* walk(dir) {
	if (!existsSync(dir)) return;
	for (const e of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
		const p = join(dir, e.name);
		if (e.isDirectory()) yield* walk(p);
		else if (/\.(vue|js|css)$/.test(e.name)) yield p;
	}
}

// Glass radius tokens, as a CSS var or as the Tailwind scale entry
const RADIUS = /var\(--g-radius-[a-z]+\)|\brounded-(?:panel|action|card|banner|tile|input|well|pill|tabbar)\b/;
const BACKGROUND = /\bbackground\s*:|\bbg-(?:glass|glass-fallback|bg|ink|brand|track-solid)\b|var\(--g-glass-fill/;

// Strip comments before counting. `direct-import` already learned this — "a
// comment naming the file is legitimate documentation" — but glass-class never
// got the same treatment, so a component that DOCUMENTS which primitive owns
// its surface was counted as building one, and the test that ENFORCES the rule
// scored five violations for quoting the class it forbids. Same defect class as
// the h1 test in views/__tests__/home-fold-budget.test.js: a rule its own prose
// can trip is not a rule.
// Deliberately naive: no string/regex awareness, because every construct that
// matters here (class="...", a CSS selector) survives comment removal intact.
const decomment = (content) =>
	content
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "")
		.replace(/^\s*\/\/.*$/gm, "");

const RULES = {
	// .g-glass is the surface class the counter keys off; a screen using it
	// directly has rebuilt a panel instead of composing GListPanel et al.
	// The guards matter: \b sits between "-" and "g", so a bare \bg-glass\b also
	// matches inside the TOKEN name --g-glass-fill-fallback, which a component
	// is entitled to use for a solid surface (§6.1). Match the class only.
	"glass-class": (content) =>
		(decomment(content).match(/(?<!-)\bg-glass(?:-ghost)?\b(?!-)/g) || []).length,

	// a line carrying both a Glass radius and a background is a hand-rolled panel
	"hand-panel": (content) =>
		decomment(content)
			.split("\n")
			.filter((l) => RADIUS.test(l) && BACKGROUND.test(l)).length,

	// an actual import, not a mention: a comment naming the file is legitimate
	// documentation, and matching the bare filename made this fire on prose
	"direct-import": (content) =>
		(content.match(/(?:^|\s)(?:@?import\s+[^\n]*|url\(\s*["']?[^)\n]*)glass-components\.css/gm) || []).length,
};

const current = {};
for (const dir of SCAN) {
	for (const file of walk(join(SRC, dir))) {
		const rel = relative(SRC, file);
		if (EXEMPT(rel)) continue;
		const content = readFileSync(file, "utf8");
		const counts = {};
		for (const [rule, fn] of Object.entries(RULES)) {
			const n = fn(content);
			if (n) counts[rule] = n;
		}
		if (Object.keys(counts).length) current[rel] = counts;
	}
}

if (UPDATE) {
	const out = {};
	for (const f of Object.keys(current).sort()) out[f] = current[f];
	writeFileSync(BASELINE_PATH, JSON.stringify(out, null, "\t") + "\n");
	console.log(`[usage] baseline updated: ${Object.keys(out).length} files recorded`);
	process.exit(0);
}

let baseline = {};
try {
	baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
} catch {
	console.error("[usage] no baseline at design/usage-baseline.json — run with --update-baseline first");
	process.exit(1);
}

const totals = {};
const fresh = [];
const strictViews = [];
for (const [file, counts] of Object.entries(current)) {
	for (const [rule, n] of Object.entries(counts)) {
		totals[rule] = (totals[rule] || 0) + n;
		const allowed = baseline[file]?.[rule] || 0;
		if (n > allowed) fresh.push(`  ${file} [${rule}] ${allowed} → ${n}`);
		// a view may not carry ANY violation, baselined or not
		else if (isView(file) && n > 0) strictViews.push(`  ${file} [${rule}] ${n} — views are strict`);
	}
}

const total = Object.values(totals).reduce((a, b) => a + b, 0);
console.log(
	`[usage] violations: ${total} total (` +
		(Object.entries(totals).map(([r, n]) => `${r}: ${n}`).join(", ") || "none") + ")"
);
if (fresh.length) {
	console.log(`[usage] NEW violations — compose a G* component instead:\n${fresh.join("\n")}`);
} else {
	console.log("[usage] no new violations above baseline");
}
if (strictViews.length) {
	console.log(`[usage] VIEWS ARE STRICT — baselined violations are not tolerated under views/:\n${strictViews.join("\n")}`);
}
console.log(
	`GATE_RESULT ${JSON.stringify({ gate: "usage", total, new: fresh.length, strictViews: strictViews.length })}`
);
process.exit(STRICT ? (total ? 1 : 0) : fresh.length || strictViews.length ? 1 : 0);
