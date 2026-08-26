// Gate 6 — visual regression (spec §16.5.6).
//
// THE GATE THAT WAS MISSING. lint, usage, contrast and surfaces all read source;
// a11y reads the DOM. None of them can see layout. A component can use every
// correct token, compose only approved primitives, sit inside the surface budget
// and still render with its icon above its label and its chevron in the next
// row — which is exactly what shipped, with all gates green.
//
// Renders every screen in frontend/e2e/screens.mjs and compares against the
// committed baselines in design/baselines/.
//
// Those baselines are MASKED — visual.spec.js hides every [data-visual-mask]
// element so relative timestamps stop rotting them — so they are not a
// faithful record of what a user sees. The unmasked set to cite in a finding
// is docs/glass/audit/screens/, written by docs/glass/audit/capture.mjs.
//
// Usage:
//   node visual.mjs                    enforce against committed baselines
//   node visual.mjs --update-baseline  re-shoot the baselines (intended changes)
//
// Needs a running site (HRMS_E2E_URL, default localhost:8080), AUDIT_PW and a
// chromium; SKIPs when any is missing, for the same reason the other render-time
// gates do — a gate that fails on every laptop without a bench gets deleted.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const UPDATE = process.argv.includes("--update-baseline");

const args = [
	"--yes",
	"playwright@1.62.1",
	"test",
	"--config=e2e/playwright.config.js",
	"e2e/visual.spec.js",
];
// "=all", not the bare flag. Bare `--update-snapshots` presets to "changed",
// which re-shoots only baselines whose comparison FAILED — so a baseline that
// drifts under the tolerance can never be corrected, because under-tolerance
// means "unchanged". That is how 26 baselines went stale through RC18 and
// stayed stale through a re-baseline that was supposed to fix them.
//
// Safe to re-shoot everything: renders here are deterministic (measured noise
// floor: 0 differing pixels), so an unchanged screen rewrites to a
// byte-identical PNG and git reports nothing. Only real changes show up in the
// diff. A baseline you cannot update is a baseline you will eventually ignore.
if (UPDATE) args.push("--update-snapshots=all");

const res = spawnSync("npx", args, {
	cwd: join(ROOT, "frontend"),
	encoding: "utf8",
	timeout: 35 * 60 * 1000,
});

const out = (res.stdout || "") + (res.stderr || "");
process.stdout.write(out);

const skip = (why) => {
	console.log(`[visual] SKIP — ${why}`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "visual", status: "skip" })}`);
	process.exit(0);
};

if (/Executable doesn't exist|browserType\.launch|playwright install/i.test(out))
	skip("chromium not installed (npx playwright@1.62.1 install chromium)");
if (/login failed/i.test(out)) skip("could not sign in — set AUDIT_PW");
if (/ECONNREFUSED|net::ERR_CONNECTION_REFUSED/i.test(out) && !/\[visual\]/.test(out))
	skip(`no site at ${process.env.HRMS_E2E_URL || "http://localhost:8080"}`);

if (UPDATE) {
	console.log("[visual] baselines re-shot into design/baselines/");
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "visual", status: "ok", baselined: true })}`);
	process.exit(0);
}

// The spec prints one "[visual]   <name>: ..." line per differing screen.
const differing = [...out.matchAll(/^\[visual\] {3}(\S+\.png):/gm)].map((m) => m[1]);
const missing = /A snapshot doesn't exist/.test(out);

if (res.status !== 0 || differing.length) {
	console.log(
		`[visual] ${differing.length} screen(s) differ from baseline` +
			(missing ? " (some baselines are missing — run with --update-baseline)" : "")
	);
	console.log(
		`GATE_RESULT ${JSON.stringify({ gate: "visual", status: "fail", differing: differing.length })}`
	);
	process.exit(1);
}

console.log("[visual] all screens match their committed baselines");
console.log(`GATE_RESULT ${JSON.stringify({ gate: "visual", status: "ok", differing: 0 })}`);
process.exit(0);
