// Gate 3 — glass surfaces per screen (spec §15: max 6, counting rule §15.1).
// Static count of the phase-2 glass recipe class per view file. A container and
// its child rows share one class occurrence = one surface; a grid of N cards
// carries the class N times = N surfaces. Report-only (exit 0) until phase 4;
// --strict fails a view over the limit.
// ponytail: static source count — an element with a glass class under v-for is
// N surfaces at runtime; flagged for manual review, DOM counting lands phase 4.

import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const VIEWS = join(ROOT, "frontend", "src", "views");
const LIMIT = 6;
const STRICT = process.argv.includes("--strict");

// the phase-2 recipe class (§6). Variants are modifiers (g-glass--ghost) on the
// same element, so counting the bare class name counts surfaces, not variants.
const SURFACE_RE = /\bg-glass\b/g;

function* walk(dir) {
	for (const e of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
		const p = join(dir, e.name);
		if (e.isDirectory()) yield* walk(p);
		else if (e.name.endsWith(".vue")) yield p;
	}
}

let over = 0;
let surfaces = 0;
let flagged = 0;
for (const file of walk(VIEWS)) {
	const content = readFileSync(file, "utf8");
	const n = (content.match(SURFACE_RE) || []).length;
	if (!n) continue;
	surfaces += n;
	const rel = relative(VIEWS, file);
	const loops = content.split("\n").filter((l) => /\bg-glass\b/.test(l) && /v-for/.test(l)).length;
	if (loops) flagged++;
	const status = n > LIMIT ? "OVER" : "ok";
	if (n > LIMIT) over++;
	console.log(`[surfaces] ${status.padEnd(4)} ${rel}: ${n}/${LIMIT}${loops ? ` (${loops} under v-for — ×N at runtime, review)` : ""}`);
}
if (!surfaces) console.log("[surfaces] no glass surfaces found (expected until phase 2 ships components)");
console.log(`GATE_RESULT ${JSON.stringify({ gate: "surfaces", surfaces, over, flagged })}`);
process.exit(STRICT && over ? 1 : 0);
