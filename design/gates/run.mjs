// Glass gates runner (spec §16.5): lint, contrast, surfaces, a11y.
//   yarn gates            report; exits 1 only on NEW lint debt or contrast fail
//   yarn gates --strict   exits 1 on any lint violation, contrast fail, or
//                         surface over budget (a11y stays report-only for now)

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const DIR = dirname(fileURLToPath(import.meta.url));
const STRICT = process.argv.includes("--strict");
const GATES = ["lint", "contrast", "surfaces", "a11y"];

const results = [];
for (const gate of GATES) {
	console.log(`\n━━ gate: ${gate} ${"━".repeat(Math.max(1, 50 - gate.length))}`);
	const res = spawnSync(process.execPath, [join(DIR, `${gate}.mjs`), ...(STRICT ? ["--strict"] : [])], {
		encoding: "utf8",
		timeout: 360000,
	});
	process.stdout.write((res.stdout || "") + (res.stderr || ""));
	const m = (res.stdout || "").match(/GATE_RESULT (\{.*\})/);
	results.push({ gate, code: res.status ?? 1, info: m ? JSON.parse(m[1]) : {} });
}

console.log("\n━━ summary " + "━".repeat(45));
console.log("gate       status  detail");
for (const { gate, code, info } of results) {
	const detail =
		gate === "lint" ? `${info.total ?? "?"} known, ${info.new ?? "?"} new`
		: gate === "contrast" ? `${info.checked ?? "?"} pairs, ${info.failures ?? "?"} failed, ${info.skipped ?? 0} skipped`
		: gate === "surfaces" ? `${info.surfaces ?? "?"} surfaces, ${info.over ?? "?"} screens over ${6}`
		: `${info.status ?? "?"} (report-only)`;
	console.log(`${gate.padEnd(10)} ${(code === 0 ? "OK" : "FAIL").padEnd(7)} ${detail}`);
}

process.exit(results.some((r) => r.code !== 0) ? 1 : 0);
