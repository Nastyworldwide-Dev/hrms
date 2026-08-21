// Glass gates runner (spec §16.5): lint, usage, contrast, surfaces, a11y, visual.
//   yarn gates            report; exits 1 only on NEW lint debt or contrast fail
//   yarn gates --strict   exits 1 on any lint violation, contrast fail, or
//                         surface over budget, a new serious a11y violation, or
//                         a screen that no longer matches its visual baseline.
//                         a11y and visual are RENDER-TIME: slow, they need a running
//                         site and SKIP without one, so a laptop with no bench
//                         still runs the four static gates.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DIR = dirname(fileURLToPath(import.meta.url));
const STRICT = process.argv.includes("--strict");
const GATES = ["lint", "usage", "contrast", "surfaces", "a11y", "visual"];

const results = [];
for (const gate of GATES) {
	console.log(`\n━━ gate: ${gate} ${"━".repeat(Math.max(1, 50 - gate.length))}`);
	// The render-time gates load every screen in the app — a11y ~76 page loads,
	// visual ~114 — and a 6-minute cap SIGTERMed the visual gate with its output
	// still buffered, so it reported FAIL with no reason printed. Static gates
	// keep the short cap; anything that drives a browser gets 30 minutes.
	const RENDER_GATES = new Set(["a11y", "visual"]);
	const res = spawnSync(process.execPath, [join(DIR, `${gate}.mjs`), ...(STRICT ? ["--strict"] : [])], {
		encoding: "utf8",
		timeout: RENDER_GATES.has(gate) ? 1_800_000 : 360_000,
	});
	process.stdout.write((res.stdout || "") + (res.stderr || ""));
	const m = (res.stdout || "").match(/GATE_RESULT (\{.*\})/);
	results.push({ gate, code: res.status ?? 1, info: m ? JSON.parse(m[1]) : {} });
}

console.log("\n━━ summary " + "━".repeat(45));
console.log("gate       status  detail");
for (const { gate, code, info } of results) {
	const detail =
		gate === "lint" || gate === "usage" ? `${info.total ?? "?"} known, ${info.new ?? "?"} new`
		: gate === "contrast" ? `${info.checked ?? "?"} pairs, ${info.failures ?? "?"} failed, ${info.skipped ?? 0} skipped`
		: gate === "surfaces" ? `${info.screens ?? "?"} screens, ${info.over ?? "?"} over 6, flattening ${info.flattening === 0 ? "held" : "BROKEN"}`
		: gate === "a11y" ? `${info.screens ?? "?"} screen-themes, ${info.known ?? 0} baselined, ${info.new ?? 0} new`
		: gate === "visual" ? `${info.differing ?? "?"} screen(s) differ from baseline`
		: `${info.status ?? "?"}`;
	console.log(`${gate.padEnd(10)} ${(code === 0 ? "OK" : "FAIL").padEnd(7)} ${detail}`);
}

process.exit(results.some((r) => r.code !== 0) ? 1 : 0);
