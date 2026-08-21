// Gate 3 — glass surfaces per screen (§15 limit of 6, counting rule §15.1).
//
// This counts what RENDERS, not what greps. It resolves component composition
// recursively, so a screen that composes GListPanel is counted even though it
// never writes the class itself.
//
// Three rules the naive version got wrong, each of which mis-counted every
// screen:
//   1. Mutually exclusive branches (v-if / v-else-if / v-else) contribute the
//      MAX of the group, not the sum — including when the branch is a child
//      COMPONENT, e.g. an error banner replacing the content it stands in for.
//   2. Components are costed by FILE PATH, not by name. Four views are called
//      Dashboard.vue; a name-keyed cache silently returns another one's count.
//   3. COUNT ONLY WHAT COMPOSITES (v1.6). A closed sheet renders nothing, so
//      its contents form a SEPARATE surface set, asserted against the same
//      limit while presented. The parent screen does not inherit them.
//
// §15.1  a glass container plus its child rows is ONE; a grid of N glass cards
//        is N. A surface component under v-for is N at runtime and is flagged.
// §15.3  the tab bar IS counted (chrome, +1 on tab destinations); the app
//        header is NOT a surface; the side nav replaces the tab bar at lg: for
//        net zero, so chrome costs 1 at every breakpoint.
// §3     the light field is not a glass surface (confirmed in 4.1).
//
//   node surfaces.mjs                exit 1 over budget (screen or sheet), on a
//                                    broken flattening invariant, or on an
//                                    uncountable v-for surface
//   node surfaces.mjs --report-only  print the counts and exit 0

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join, relative, basename } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SRC = join(ROOT, "frontend", "src");
const LIMIT = 6;
const REPORT_ONLY = process.argv.includes("--report-only");

const GLASS = /(?<!-)\bg-glass(?:-ghost)?\b(?!-)/g;
// anything that presents over the page rather than in it
const SHEET_TAGS = /^(GModal|GConfirm|GActionSheet|ion-modal)$/;

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

// name → file, for resolving child TAGS (referenced by imported name, so
// basename is right there). Screens are costed by path — see rule 2.
const components = new Map();
for (const f of walk(join(SRC, "components"))) components.set(basename(f, ".vue"), f);
for (const f of walk(join(SRC, "views"))) {
	const b = basename(f, ".vue");
	if (!components.has(b)) components.set(b, f);
}

const template = (file) => {
	const m = readFileSync(file, "utf8").match(/<template>([\s\S]*)<\/template>/);
	return m ? stripComments(m[1]) : "";
};

const memo = new Map();
const loops = new Map(); // component → [child names rendered under v-for]

/** @returns {{screen: number, sheets: number[]}} */
function costFile(file, seen = new Set()) {
	if (memo.has(file)) return memo.get(file);
	if (seen.has(file)) return { screen: 0, sheets: [] };
	seen.add(file);

	const name = basename(file, ".vue");
	const tpl = template(file);

	let screen = 0;
	const sheets = [];
	let sheetDepth = 0;
	let openSheet = 0;
	let branch = null;
	const loopedHere = [];

	// route a count to the screen, or to the sheet currently open
	const add = (n) => {
		if (!n) return;
		if (sheetDepth > 0) openSheet += n;
		else screen += n;
	};

	const lines = tpl.split("\n");
	// a component tag often spans several lines, with v-for below the tag name.
	// Look ahead to the element's ">" so a multi-line <GIssueCard\n v-for=…> is
	// still recognised as N surfaces at runtime (§15.1).
	const elementHasVFor = (idx) => {
		for (let k = idx; k < Math.min(idx + 12, lines.length); k++) {
			if (/\bv-for=/.test(lines[k])) return true;
			if (/>/.test(lines[k]) && k > idx) return false;
			if (k === idx && /\/?>/.test(lines[k].replace(/<[A-Za-z][^\s>]*/, ""))) return /\bv-for=/.test(lines[k]);
		}
		return false;
	};
	for (const [lineIndex, line] of lines.entries()) {
		const opens = [...line.matchAll(/<([A-Za-z][A-Za-z0-9-]*)\b(?![^>]*\/>)/g)].filter((m) =>
			SHEET_TAGS.test(m[1])
		).length;
		const closes = [...line.matchAll(/<\/([A-Za-z][A-Za-z0-9-]*)>/g)].filter((m) =>
			SHEET_TAGS.test(m[1])
		).length;
		if (opens) {
			if (sheetDepth === 0) openSheet = 0;
			sheetDepth += opens;
		}

		// everything this line contributes: its own glass plus the screen cost
		// of every component it renders
		let lineTotal = (line.match(GLASS) || []).length;
		for (const m of line.matchAll(/<([A-Z][A-Za-z0-9]*)\b/g)) {
			const child = m[1];
			if (!components.has(child) || child === name) continue;
			const c = costFile(components.get(child), new Set(seen));
			if (SHEET_TAGS.test(child)) {
				// a child that IS a sheet never adds to the screen
				sheets.push(...c.sheets, c.screen);
			} else {
				lineTotal += c.screen;
				sheets.push(...c.sheets);
			}
			if (c.screen > 0 && elementHasVFor(lineIndex)) loopedHere.push(child);
		}

		if (/\bv-if=/.test(line)) {
			if (branch !== null) add(branch);
			branch = lineTotal;
		} else if (/\bv-else-if=|\bv-else\b/.test(line)) {
			branch = Math.max(branch ?? 0, lineTotal);
		} else if (branch !== null && lineTotal) {
			// A v-if with no v-else must not swallow everything after it: the
			// group closes as soon as a line with no branch directive carries a
			// surface. Without this, Home's check-in sheet reported 1 surface
			// where it renders 2 — the map is inside a v-if, the selfie is not.
			add(branch);
			branch = null;
			add(lineTotal);
		} else {
			add(lineTotal);
		}

		if (closes) {
			sheetDepth = Math.max(0, sheetDepth - closes);
			if (sheetDepth === 0 && openSheet > 0) {
				sheets.push(openSheet);
				openSheet = 0;
			}
		}
	}

	if (branch !== null) add(branch);
	if (sheetDepth > 0 && openSheet > 0) sheets.push(openSheet);
	if (loopedHere.length) loops.set(name, loopedHere);

	const result = { screen, sheets: sheets.filter((n) => n > 0) };
	memo.set(file, result);
	return result;
}

const cost = (name) => {
	const file = components.get(name);
	return file ? costFile(file) : { screen: 0, sheets: [] };
};

// which views sit under TabbedView, and therefore render the tab bar (§15.3)
const tabbed = new Set();
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
	for (const m of router.slice(start, end).matchAll(/@\/views\/([A-Za-z0-9/]+)\.vue/g))
		tabbed.add(basename(m[1]));
} catch {
	/* router shape changed — chrome falls back to 0 */
}

const rows = [];
for (const file of walk(join(SRC, "views"))) {
	const name = basename(file, ".vue");
	if (name === "DesignSpecimen") continue; // renders every component by design
	const c = costFile(file);
	const chrome = tabbed.has(name) ? 1 : 0;
	rows.push({
		rel: relative(SRC, file),
		content: c.screen,
		sheets: c.sheets,
		chrome,
		total: c.screen + chrome,
	});
}

let over = 0;
for (const r of rows.sort((a, b) => b.total - a.total || a.rel.localeCompare(b.rel))) {
	if (r.total === 0 && !r.sheets.length) continue;
	if (r.total > LIMIT) over++;
	console.log(
		`[surfaces] ${(r.total > LIMIT ? "OVER" : "ok").padEnd(4)} ${r.rel.padEnd(44)} ` +
			`${String(r.total).padStart(2)}/${LIMIT}  (content ${r.content}${r.chrome ? " + tab bar 1" : ""})` +
			(r.sheets.length ? `  · sheets: ${r.sheets.join(", ")}` : "")
	);
}

// each sheet is asserted on its own — that is what composites while presented
let sheetOver = 0;
for (const r of rows) {
	for (const [i, n] of r.sheets.entries()) {
		if (n > LIMIT) {
			sheetOver++;
			console.log(`[surfaces] OVER ${r.rel} sheet ${i + 1}: ${n}/${LIMIT} while presented (§15.1)`);
		}
	}
}

// A glass surface under v-for is N surfaces at runtime and the gate cannot
// compute N, so the default is to fail: §15.2's answer is to flatten the list
// into one panel, as the balance grid, stat row and issue list all do.
//
// The one legitimate exception is a list bounded by ADMINISTRATOR CONFIGURATION
// rather than user data — a handful of SSO providers, not an employee's issue
// history. That exception must be DECLARED in the source, not inferred here, so
// a reviewer can grep for it:
//     glass-surfaces: bounded — <reason>
const BOUNDED = /glass-surfaces:\s*bounded\s*—/;
let undeclaredLoops = 0;
for (const [name, children] of loops) {
	const file = components.get(name);
	const declared = file && BOUNDED.test(readFileSync(file, "utf8"));
	if (!declared) undeclaredLoops++;
	console.log(
		`[surfaces] ${declared ? "NOTE" : "FAIL"} ${name}: ${children.join(", ")} render under v-for — ` +
			(declared
				? "N surfaces at runtime, declared bounded in the source (§15.1)"
				: "N surfaces at runtime and N is not computable. Flatten to one panel (§15.2), or declare it bounded in the source")
	);
}

// ---------- §15.2 flattening invariant ----------
// Asserted rather than trusted: if someone re-glasses the cells, three screens
// silently go back over budget without any screen changing.
const FLATTENED = [
	{ name: "GBalanceGrid", expect: 1, was: 4, note: "2×2 balance grid → one panel (§15.2)" },
	{ name: "GStatPanel", expect: 1, was: 3, note: "3-up stat row → one panel (§15.2)" },
	{ name: "GListPanel", expect: 1, was: null, note: "container + child rows = one (§15.1)" },
];
let flatteningBroken = 0;
for (const f of FLATTENED) {
	const actual = cost(f.name).screen;
	const ok = actual === f.expect;
	if (!ok) flatteningBroken++;
	console.log(
		`[surfaces] ${ok ? "PASS" : "FAIL"} ${f.name} renders ${actual} surface(s), expected ${f.expect}` +
			(f.was ? ` — was ${f.was} before flattening` : "") +
			` · ${f.note}`
	);
}
// the counter-case: N glass cards must count as N, not collapse to 1
const gridOfFour = cost("GIssueCard").screen * 4;
if (gridOfFour !== 4) flatteningBroken++;
console.log(
	`[surfaces] ${gridOfFour === 4 ? "PASS" : "FAIL"} four GIssueCards render ${gridOfFour} surfaces ` +
		`— §15.1's "a grid of N glass cards counts as N", the rule flattening must not break`
);

console.log(
	`[surfaces] ${rows.filter((r) => r.total > 0).length} screens counted, ${over} over the limit of ${LIMIT}` +
		`; ${rows.reduce((a, r) => a + r.sheets.length, 0)} sheet surface sets, ${sheetOver} over`
);
console.log(
	`GATE_RESULT ${JSON.stringify({
		gate: "surfaces",
		screens: rows.length,
		over,
		sheetOver,
		flattening: flatteningBroken,
		looped: loops.size,
		undeclaredLoops,
	})}`
);
process.exit(!REPORT_ONLY && (over || sheetOver || flatteningBroken || undeclaredLoops) ? 1 : 0);
