// Gate 1 — token discipline (spec §16.5.1).
// Scans frontend/src/**/*.{vue,js,css} for hex/rgb()/hsl() literals, arbitrary
// Tailwind values and outline:none without a focus replacement.
// Existing debt lives in design/lint-baseline.json (per file, per rule, counts);
// NEW violations (count above baseline) fail even in default mode.
//   node lint.mjs                  report; exit 1 only on new violations
//   node lint.mjs --strict         exit 1 on any violation
//   node lint.mjs --update-baseline  rewrite the baseline to current counts

import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SRC = join(ROOT, "frontend", "src");
const BASELINE_PATH = join(ROOT, "design", "lint-baseline.json");
const STRICT = process.argv.includes("--strict");
const UPDATE = process.argv.includes("--update-baseline");

// generated theme files + modernist.css are exempt (spec: excluded); everything
// else — including legacy variables.css — is debt the baseline carries
const EXCLUDE = new Set([
	"theme/glass.css",
	"theme/glass.variables.css",
	"theme/modernist.css",
]);

function* walk(dir) {
	for (const e of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
		const p = join(dir, e.name);
		if (e.isDirectory()) yield* walk(p);
		else if (/\.(vue|js|css)$/.test(e.name)) yield p;
	}
}

const count = (content, re) => (content.match(re) || []).length;

// outline: none|0 inside a rule block with no focus replacement in the block
function outlineViolations(file, content) {
	const cssChunks =
		file.endsWith(".css") ? [content]
		: file.endsWith(".vue") ? [...content.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1])
		: [];
	let n = 0;
	for (const css of cssChunks) {
		for (const [block] of css.matchAll(/\{[^{}]*\}/g)) {
			if (/outline\s*:\s*(?:none|0)\b/.test(block) && !/box-shadow|outline-offset|border\s*:/.test(block)) n++;
		}
	}
	return n;
}


// A component's <style scoped> must not redefine a class the theme layer owns.
//
// TWICE NOW a specificity collision has silently overridden the design system
// and this gate was blind to both, because it reads files one at a time and
// theme/glass-components.css is the only place it expects component styling:
//
//   .g-field     was defined twice INSIDE the theme file — the §3 light field
//                and the GInput wrapper — so position:absolute and
//                pointer-events:none landed on every form field and the login
//                screen could not be clicked (8.1).
//   .g-seg__option / .g-header__avatar-link  were redefined in a component's
//                scoped block, which carries a [data-v-*] attribute and
//                therefore outranks the theme layer INCLUDING ITS MEDIA
//                QUERIES. One made every segmented option 6px under the touch
//                minimum; the other un-hid the header avatar at lg:, so
//                identity rendered twice on desktop (8.16).
//
// Scoped blocks are still fine for classes the theme layer does not own.
let themeSelectors = null;
function themeOwnedClasses() {
	if (themeSelectors) return themeSelectors;
	themeSelectors = new Set();
	const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
	for (const m of css.matchAll(/(?:^|\n)([^{}\n]*)\{/g)) {
		for (const part of m[1].split(",")) {
			const sel = part.trim();
			if (/^\.[a-zA-Z0-9_-]+$/.test(sel)) themeSelectors.add(sel.slice(1));
		}
	}
	return themeSelectors;
}

function scopedOverrides(file, content) {
	if (!file.endsWith(".vue")) return 0;
	const owned = themeOwnedClasses();
	let n = 0;
	for (const m of content.matchAll(/<style[^>]*\bscoped\b[^>]*>([\s\S]*?)<\/style>/g)) {
		const body = m[1].replace(/\/\*[\s\S]*?\*\//g, "");
		for (const r of body.matchAll(/(?:^|\n)\s*\.([a-zA-Z0-9_-]+)\s*[,{]/g)) {
			if (owned.has(r[1])) n++;
		}
	}
	return n;
}

const RULES = {
	hex: (f, c) => count(c, /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b/g),
	colorfn: (f, c) => count(c, /\b(?:rgba?|hsla?)\(\s*(?!var\b)/g),
	arbitrary: (f, c) => count(c, /[a-zA-Z][\w:/.%-]*-\[[^\]\n]+\]/g),
	outline: outlineViolations,
	scopedOverride: scopedOverrides,
};

const current = {};
for (const file of walk(SRC)) {
	const rel = relative(SRC, file);
	if (EXCLUDE.has(rel)) continue;
	const content = readFileSync(file, "utf8");
	const counts = {};
	for (const [rule, fn] of Object.entries(RULES)) {
		const n = fn(file, content);
		if (n) counts[rule] = n;
	}
	if (Object.keys(counts).length) current[rel] = counts;
}

if (UPDATE) {
	const sortedOut = {};
	for (const f of Object.keys(current).sort()) sortedOut[f] = current[f];
	writeFileSync(BASELINE_PATH, JSON.stringify(sortedOut, null, "\t") + "\n");
	console.log(`[lint] baseline updated: ${Object.keys(sortedOut).length} files recorded`);
	process.exit(0);
}

let baseline = {};
try {
	baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
} catch {
	console.error("[lint] no baseline at design/lint-baseline.json — run with --update-baseline first");
	process.exit(1);
}

const totals = {};
const fresh = [];
for (const [file, counts] of Object.entries(current)) {
	for (const [rule, n] of Object.entries(counts)) {
		totals[rule] = (totals[rule] || 0) + n;
		const allowed = baseline[file]?.[rule] || 0;
		if (n > allowed) fresh.push(`  ${file} [${rule}] ${allowed} → ${n}`);
	}
}

const total = Object.values(totals).reduce((a, b) => a + b, 0);
console.log(
	`[lint] violations: ${total} total (` +
		Object.entries(totals).map(([r, n]) => `${r}: ${n}`).join(", ") + ")"
);
if (fresh.length) {
	console.log(`[lint] NEW violations above baseline:\n${fresh.join("\n")}`);
} else {
	console.log("[lint] no new violations above baseline");
}
console.log(`GATE_RESULT ${JSON.stringify({ gate: "lint", total, new: fresh.length })}`);
process.exit(STRICT ? (total ? 1 : 0) : fresh.length ? 1 : 0);
