// Gate 4 — axe a11y harness (report-only for now, spec §16.5.4).
// Runs frontend/e2e/a11y.spec.js through the repo's existing pinned-playwright
// convention. Needs a running site (HRMS_E2E_URL, default localhost:8000) and
// an installed chromium; when either is missing this reports SKIP, because a
// gate that fails on every laptop without a bench gets deleted, not fixed.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));

const res = spawnSync(
	"npx",
	["--yes", "playwright@1.62.1", "test", "--config=e2e/playwright.config.js", "e2e/a11y.spec.js"],
	{ cwd: join(ROOT, "frontend"), encoding: "utf8", timeout: 300000 }
);

const out = (res.stdout || "") + (res.stderr || "");
process.stdout.write(out);

let status = "ok";
if (res.status !== 0) {
	if (/Executable doesn't exist|browserType.launch|playwright install/i.test(out)) {
		status = "skip";
		console.log("[a11y] SKIP — chromium not installed (npx playwright@1.62.1 install chromium)");
	} else if (/ECONNREFUSED|ERR_CONNECTION|Timeout.*goto|net::ERR/i.test(out)) {
		status = "skip";
		console.log("[a11y] SKIP — no site at HRMS_E2E_URL (default http://localhost:8000)");
	} else {
		status = "issues";
		console.log("[a11y] issues found — REPORT ONLY, not enforced until screens exist");
	}
}
console.log(`GATE_RESULT ${JSON.stringify({ gate: "a11y", status })}`);
process.exit(0); // report-only by design, in both modes, until phase 4
