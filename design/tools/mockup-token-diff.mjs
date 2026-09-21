// Re-derives every number in .claude/plans/phase2-token-delta.md.
//
// That file's figures were first produced by an ad-hoc script in /tmp, so no
// reader could check them and no editor could refresh them. Four of its counts
// drifted before this existed — each time by quoting a number from one
// measurement next to a number from another. The two passes below are printed
// with their own denominators, separately, and never summed.
//
// Usage: node design/tools/mockup-token-diff.mjs
// Exit 2 if the mockup is absent ("Nadi PWA UI UX 2.0" is gitignored).

import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SHIPPED = join(ROOT, "frontend", "src", "theme", "glass.css");
const MOCKUP = join(ROOT, "Nadi PWA UI UX 2.0", "nadi-2.0-mockup-4.html");

// glass.css is OUTPUT 1 of build-tokens.mjs and holds the --g-* tokens.
// glass.variables.css is output 3 and holds five --ion-* variables; diffing
// against it reports a nonsensical zero overlap. This mistake cost a pass.
if (!existsSync(MOCKUP)) {
	console.error(
		`mockup not found at ${MOCKUP}\n` +
			'"Nadi PWA UI UX 2.0" is gitignored, so it is not in a fresh checkout.',
	);
	process.exit(2);
}

const norm = (v) => v.trim().replace(/\s+/g, " ").replace(/, /g, ",").toLowerCase();

// The dark selector differs between the two files: glass.css writes
// html[data-theme="dark"], the mockup writes a bare [data-theme="dark"].
// A regex requiring the html prefix silently returns an EMPTY dark set, which
// reads as "0 shared" rather than as an error. Match both.
const DARK = /(?:html)?\s*\[data-theme=["']?dark["']?\]\s*\{|prefers-color-scheme:\s*dark/;

function props(text, theme) {
	const i = text.search(DARK);
	if (theme === "dark") {
		if (i < 0) throw new Error("no dark block found — selector regex is wrong");
		text = text.slice(i);
	} else if (i > 0) {
		text = text.slice(0, i);
	}
	const out = {};
	for (const m of text.matchAll(/(--g-[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
		if (!(m[1] in out)) out[m[1]] = norm(m[2]); // first declaration wins
	}
	return out;
}

const shippedSrc = readFileSync(SHIPPED, "utf8");
const mockupSrc = readFileSync(MOCKUP, "utf8");

const allShipped = new Set(
	[...shippedSrc.matchAll(/(--g-[a-z0-9-]+)\s*:/g)].map((m) => m[1]),
);
const allMockup = new Set(
	[...mockupSrc.matchAll(/(--g-[a-z0-9-]+)\s*:/g)].map((m) => m[1]),
);

console.log(`names: ${allShipped.size} shipped, ${allMockup.size} mockup`);

const onlyMockup = [...allMockup].filter((n) => !allShipped.has(n)).sort();
console.log(`\nin mockup, not shipped (${onlyMockup.length}): ${onlyMockup.join(", ")}`);

// The two passes. Printed with their own denominators and never added: a
// (token, theme) pair count divided by the light denominator is how "5 of 53"
// gets written.
const differing = new Set();
for (const theme of ["light", "dark"]) {
	const s = props(shippedSrc, theme);
	const m = props(mockupSrc, theme);
	const shared = Object.keys(m).filter((k) => k in s).sort();
	const diff = shared.filter((k) => s[k] !== m[k]);
	diff.forEach((k) => differing.add(k));
	console.log(
		`\n${theme.toUpperCase()}: ${shared.length} shared, ` +
			`${shared.length - diff.length} identical, ${diff.length} differ`,
	);
	for (const k of diff) console.log(`  ${k}\n      shipped: ${s[k]}\n      mockup : ${m[k]}`);
}

console.log(
	`\ndistinct tokens differing in at least one theme: ${differing.size} ` +
		`(${[...differing].sort().join(", ")})`,
);
console.log("Do not sum the two passes: they measure different name sets.");
