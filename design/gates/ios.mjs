// Gate 11 — the iOS rules, measured in Safari's engine (alpha.9 plan step 6:
// "lock it in"). Four audits that each found real defects by hand now fail
// the board when a screen or sheet breaks them again:
//   ios-consistency-audit   pages: gutter, one radius, type ramp, header
//                           inset and gap, button height, nothing loose
//   sheet-consistency-audit the same rules inside every tappable sheet
//   scroll-and-shift-audit  pages: nothing scrolls past its end, nothing
//                           moves while loading (first visit AND return visit)
//   sheet-shift-audit       sheets: nothing moves after opening, no overrun,
//                           scroll stays in the sheet
// Needs a served site and AUDIT_PW; SKIPs without, like a11y/visual/coherence.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const AUDITS = [
	"ios-consistency-audit",
	"sheet-consistency-audit",
	"scroll-and-shift-audit",
	"sheet-shift-audit",
];

const skip = (why) => {
	console.log(`[ios] SKIP — ${why}`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "ios", status: "skip" })}`);
	process.exit(0);
};
if (!process.env.AUDIT_PW && !process.env.HRMS_E2E_PW) skip("could not sign in — set AUDIT_PW");

let failed = 0;
const counts = {};
for (const audit of AUDITS) {
	const res = spawnSync(process.execPath, [join("e2e", `${audit}.mjs`)], {
		cwd: join(ROOT, "frontend"),
		encoding: "utf8",
		timeout: 15 * 60 * 1000,
		env: process.env,
	});
	const out = (res.stdout || "") + (res.stderr || "");
	if (/login failed|401|ECONNREFUSED/i.test(out) && !/GATE_COUNT/.test(out)) skip(`${audit}: no served site`);
	const n = Number((out.match(/GATE_COUNT (\d+)/) || [])[1] ?? NaN);
	counts[audit] = Number.isNaN(n) ? "error" : n;
	if (res.status !== 0) {
		failed++;
		console.log(`[ios] FAIL ${audit}:\n${out.split("\n").filter((l) => l.trim()).slice(-12).join("\n")}`);
	} else {
		console.log(`[ios] OK ${audit} — 0 findings`);
	}
}
console.log(`GATE_RESULT ${JSON.stringify({ gate: "ios", status: failed ? "fail" : "ok", ...counts })}`);
process.exit(failed ? 1 : 0);
