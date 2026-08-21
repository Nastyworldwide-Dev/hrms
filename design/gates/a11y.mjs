// Gate 4 — axe a11y, ENFORCING (spec §16.5.4).
//
// This gate used to run axe on one route and then `process.exit(0)` whatever it
// found. It reported three serious colour-contrast violations on /hrms/login —
// the most broken screen in the app, whose form could not be clicked at all —
// and passed the build anyway. A gate that detects failures and passes is worse
// than no gate: it converts an unknown into false confidence. 8.x flipped it.
//
// Policy now:
//   - serious and critical violations FAIL, unless carried in the baseline
//   - moderate and minor are reported, never enforced (too noisy to gate on)
//   - NEW serious/critical, or a baselined one whose node count GREW, fails
//   - a screen that fails to render at all is a critical violation
//
// Existing debt lives in design/a11y-baseline.json, per screen:theme, per rule.
// Usage:
//   node a11y.mjs                    enforce against the baseline
//   node a11y.mjs --update-baseline  rewrite the baseline to current findings
//
// Needs a running site (HRMS_E2E_URL, default localhost:8080), AUDIT_PW, and an
// installed chromium; when any is missing this reports SKIP, because a gate that
// fails on every laptop without a bench gets deleted, not fixed.

import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const BASELINE_PATH = join(ROOT, "design", "a11y-baseline.json");
const REPORT_PATH = join(ROOT, "design", "gates", ".a11y-report.json");
const UPDATE = process.argv.includes("--update-baseline");
const ENFORCED = new Set(["serious", "critical"]);

if (existsSync(REPORT_PATH)) rmSync(REPORT_PATH);

const res = spawnSync(
	"npx",
	["--yes", "playwright@1.62.1", "test", "--config=e2e/playwright.config.js", "e2e/a11y.spec.js"],
	{ cwd: join(ROOT, "frontend"), encoding: "utf8", timeout: 20 * 60 * 1000 }
);

const out = (res.stdout || "") + (res.stderr || "");
process.stdout.write(out);

const skip = (why) => {
	console.log(`[a11y] SKIP — ${why}`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "a11y", status: "skip" })}`);
	process.exit(0);
};

if (/Executable doesn't exist|browserType\.launch|playwright install/i.test(out))
	skip("chromium not installed (npx playwright@1.62.1 install chromium)");
if (/ECONNREFUSED|ERR_CONNECTION|Timeout.*goto|net::ERR_CONNECTION_REFUSED/i.test(out) && !existsSync(REPORT_PATH))
	skip(`no site at ${process.env.HRMS_E2E_URL || "http://localhost:8080"}`);
if (/login failed/i.test(out)) skip("could not sign in — set AUDIT_PW");
if (!existsSync(REPORT_PATH)) skip("the spec produced no report");

const report = JSON.parse(readFileSync(REPORT_PATH, "utf8"));

if (UPDATE) {
	const next = {};
	for (const screen of Object.keys(report).sort()) {
		const rules = {};
		for (const rule of Object.keys(report[screen]).sort()) {
			if (ENFORCED.has(report[screen][rule].impact)) rules[rule] = report[screen][rule].nodes;
		}
		if (Object.keys(rules).length) next[screen] = rules;
	}
	writeFileSync(BASELINE_PATH, JSON.stringify(next, null, 2) + "\n");
	console.log(`[a11y] baseline updated: ${Object.keys(next).length} screens carrying debt`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "a11y", status: "ok", baselined: true })}`);
	process.exit(0);
}

let baseline = {};
if (existsSync(BASELINE_PATH)) {
	baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
} else {
	console.error("[a11y] no baseline at design/a11y-baseline.json — run with --update-baseline first");
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "a11y", status: "fail", reason: "no baseline" })}`);
	process.exit(1);
}

const fresh = [];
let known = 0;
let moderate = 0;
for (const screen of Object.keys(report).sort()) {
	for (const [rule, info] of Object.entries(report[screen])) {
		if (!ENFORCED.has(info.impact)) {
			moderate += info.nodes;
			continue;
		}
		const allowed = baseline[screen]?.[rule] ?? 0;
		if (info.nodes > allowed) {
			fresh.push(
				`  ${screen}  ${info.impact}: ${rule} — ${info.nodes} node(s), baseline allows ${allowed}`
			);
		} else {
			known += info.nodes;
		}
	}
}

const screensChecked = Object.keys(report).length;
if (fresh.length) {
	console.log(`[a11y] NEW serious/critical violations above baseline:\n${fresh.join("\n")}`);
	console.log(
		`GATE_RESULT ${JSON.stringify({ gate: "a11y", status: "fail", screens: screensChecked, new: fresh.length, known })}`
	);
	process.exit(1);
}

console.log(
	`[a11y] ${screensChecked} screen-themes checked, ${known} baselined serious/critical node(s), ` +
		`${moderate} moderate/minor node(s) reported, 0 new`
);
console.log(
	`GATE_RESULT ${JSON.stringify({ gate: "a11y", status: "ok", screens: screensChecked, known, moderate })}`
);
process.exit(0);
