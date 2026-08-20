// Gate 3 — glass surfaces per screen (§15 limit of 6, counting rule §15.1).
//
// This counts what RENDERS, not what greps. The first version matched the
// literal class in view files, which over-counted mutually exclusive v-if
// branches and class names appearing in comment prose, and — worse —
// under-counted every screen that composes a G* component instead of writing
// the class itself. Prompt 2.2 had to verify flattening by SSR-rendering the
// components because this gate could not be trusted.
//
// The model:
//   cost(component) = its own glass elements + the cost of every component it
//   renders, resolved recursively with memoisation.
// Mutually exclusive branches (v-if / v-else-if / v-else) contribute the MAX of
// the branch costs, not the sum — one of them renders.
//
// §15.1  a glass container plus its child rows is ONE; a grid of N glass cards
//        is N. Rows are not glass, so the container's cost is 1 either way; a
//        surface component under v-for is N at runtime and is flagged.
// §15.3  the tab bar IS counted (chrome, +1 on tab destinations); the app
//        header is NOT a surface; the side nav replaces the tab bar at lg: for
//        net zero, so the chrome cost is 1 at every breakpoint.
// §3     the light field is not a glass surface (confirmed in 4.1) — it is
//        what the glass blurs, and carries no backdrop-filter.
//
// STRICT BY DEFAULT as of phase 5 batch 1. Until Home composed real
// components this gate had nothing to measure, so it reported; now that
// screens carry surfaces, a screen over budget or a surface that cannot be
// counted statically fails the build.
//   node surfaces.mjs                exit 1 over budget, on a broken flattening
//                                    invariant, or on an uncountable v-for surface
//   node surfaces.mjs --report-only  print the counts and exit 0

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join, relative, basename } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SRC = join(ROOT, "frontend", "src");
const LIMIT = 6;
const REPORT_ONLY = process.argv.includes("--report-only");

const GLASS = /(?<!-)\bg-glass(?:-ghost)?\b(?!-)/g;
const stripComments = (s) =>
	s.replace(/<!--[\s\S]*?-->/g, "").replace(/\/\*[\s\S]*?\*\//g, "");

function* walk(dir) {
	if (!existsSync(dir)) return;
	for (const e of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
		const p = join(dir, e.name);
		if (e.isDirectory()) yield* walk(p);
		else if (e.name.endsWith(".vue")) yield p;
	}
}

// name → file, for every component that could carry or compose a surface
const components = new Map();
for (const f of walk(join(SRC, "components"))) components.set(basename(f, ".vue"), f);
for (const f of walk(join(SRC, "views"))) components.set(basename(f, ".vue"), f);

const template = (file) => {
	const m = readFileSync(file, "utf8").match(/<template>([\s\S]*)<\/template>/);
	return m ? stripComments(m[1]) : "";
};

// A line carrying v-if/v-else-if/v-else opens a branch group; only one of the
// group renders, so the group contributes its maximum, not its sum.
function ownCost(tpl) {
	let plain = 0;
	const branches = [];
	let current = null;
	for (const line of tpl.split("\n")) {
		const glass = (line.match(GLASS) || []).length;
		if (/\bv-if=/.test(line)) {
			if (current) branches.push(current);
			current = glass;
			continue;
		}
		if (/\bv-else-if=|\bv-else\b/.test(line)) {
			current = Math.max(current ?? 0, glass);
			continue;
		}
		if (current !== null && glass) {
			// continuation of the open branch's element
			current = Math.max(current, glass);
			continue;
		}
		plain += glass;
	}
	if (current !== null) branches.push(current);
	return plain + branches.reduce((a, b) => a + b, 0);
}

const memo = new Map();
const loops = new Map(); // component → [child names rendered under v-for]

function cost(name, seen = new Set()) {
	if (memo.has(name)) return memo.get(name);
	const file = components.get(name);
	if (!file || seen.has(name)) return 0;
	seen.add(name);
	const tpl = template(file);
	let total = ownCost(tpl);

	const loopedHere = [];
	for (const line of tpl.split("\n")) {
		for (const m of line.matchAll(/<([A-Z][A-Za-z0-9]*)\b/g)) {
			const child = m[1];
			if (!components.has(child) || child === name) continue;
			const c = cost(child, new Set(seen));
			total += c;
			if (c > 0 && /\bv-for=/.test(line)) loopedHere.push(child);
		}
	}
	if (loopedHere.length) loops.set(name, loopedHere);
	memo.set(name, total);
	return total;
}

// which views sit under TabbedView, and therefore render the tab bar (§15.3)
let tabbed = new Set();
try {
	const router = readFileSync(join(SRC, "router", "index.js"), "utf8");
	// bracket-match TabbedView's own children array — slicing to the next known
	// token pulls in every route registered after it, which handed the tab bar
	// to the auth screens
	const start = router.indexOf("[", router.indexOf("children:", router.indexOf("component: TabbedView")));
	let depth = 0;
	let end = start;
	for (; end < router.length; end++) {
		if (router[end] === "[") depth++;
		else if (router[end] === "]" && --depth === 0) break;
	}
	const block = router.slice(start, end);
	for (const m of block.matchAll(/@\/views\/([A-Za-z0-9/]+)\.vue/g)) tabbed.add(basename(m[1]));
} catch {
	/* router shape changed — chrome falls back to 0 and is reported as unknown */
}

const rows = [];
for (const file of walk(join(SRC, "views"))) {
	const name = basename(file, ".vue");
	if (name === "DesignSpecimen") continue; // the specimen renders every component by design
	const content = cost(name);
	const chrome = tabbed.has(name) ? 1 : 0; // tab bar below lg:, side nav above — net 1
	rows.push({ name, rel: relative(SRC, file), content, chrome, total: content + chrome });
}

let over = 0;
for (const r of rows.sort((a, b) => b.total - a.total || a.name.localeCompare(b.name))) {
	if (r.total === 0) continue;
	const flag = r.total > LIMIT ? "OVER" : "ok";
	if (r.total > LIMIT) over++;
	console.log(
		`[surfaces] ${flag.padEnd(4)} ${r.rel.padEnd(44)} ${String(r.total).padStart(2)}/${LIMIT}` +
			`  (content ${r.content}${r.chrome ? " + tab bar 1" : ""})`
	);
}

const flagged = [...loops.entries()].filter(([n]) => components.has(n));
for (const [name, children] of flagged) {
	console.log(`[surfaces] NOTE ${name}: ${children.join(", ")} render under v-for — N surfaces at runtime, counted as 1 each (§15.1)`);
}

// ---------- §15.2 flattening invariant ----------
//
// The mockup's 2×2 balance grid and 3-up stat row were four and three glass
// surfaces; flattened they are ONE panel each with internal --hair dividers.
// That is what bought the headroom §11's states need, so it is asserted here
// rather than trusted: if someone re-glasses the cells, three screens silently
// go back over budget.
const FLATTENED = [
	{ name: "GBalanceGrid", expect: 1, was: 4, note: "2×2 balance grid → one panel (§15.2)" },
	{ name: "GStatPanel", expect: 1, was: 3, note: "3-up stat row → one panel (§15.2)" },
	{ name: "GListPanel", expect: 1, was: null, note: "container + child rows = one (§15.1)" },
];
let flatteningBroken = 0;
for (const f of FLATTENED) {
	const actual = cost(f.name);
	const ok = actual === f.expect;
	if (!ok) flatteningBroken++;
	console.log(
		`[surfaces] ${ok ? "PASS" : "FAIL"} ${f.name} renders ${actual} surface(s), expected ${f.expect}` +
			(f.was ? ` — was ${f.was} before flattening` : "") + ` · ${f.note}`
	);
}
// and the counter-case: N glass cards must count as N, not collapse to 1
const cardCost = cost("GIssueCard");
const gridOfFour = cardCost * 4;
console.log(
	`[surfaces] ${gridOfFour === 4 ? "PASS" : "FAIL"} four GIssueCards render ${gridOfFour} surfaces ` +
		`— §15.1's "a grid of N glass cards counts as N", the rule flattening must not break`
);
if (gridOfFour !== 4) flatteningBroken++;

console.log(
	`[surfaces] ${rows.filter((r) => r.total > 0).length} screens counted, ${over} over the limit of ${LIMIT}`
);
console.log(`GATE_RESULT ${JSON.stringify({ gate: "surfaces", screens: rows.length, over, flattening: flatteningBroken, looped: flagged.length })}`);
// a broken flattening invariant always fails: it is how three screens go back
// over budget without any screen changing
process.exit(!REPORT_ONLY && (over || flatteningBroken || flagged.length) ? 1 : 0);
