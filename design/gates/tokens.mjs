// Gate 7 — ROLE–TOKEN BINDING and TOKEN COLLAPSE (spec §16.5.2).
//
// Two static checks the other gates cannot express, both learned from the same
// defect: `bg-accent` painted #3F5C00 dark olive because `accent.DEFAULT`
// resolved to --accent-ink while accent-100 resolved to --brand. Eight form
// submits wrote it expecting chartreuse.
//
//   1. ROLE–TOKEN BINDING. lint checks that a colour is not a raw literal. It
//      cannot check that the colour is the RIGHT ONE for the role, because
//      `bg-accent` is spelled correctly — it just means the wrong thing. This
//      asserts the aliases a role depends on resolve to the token that role
//      requires.
//
//   2. TOKEN COLLAPSE. The defect survived a 148-finding audit because
//      --accent-ink EQUALS --brand in dark theme. Two tokens that are distinct
//      in one theme and identical in another create a blind spot: whichever
//      theme collapses them renders the wrong one correctly. Every such pair is
//      reported, because each is a place a swap can hide.
//
// Static — reads tokens.json, glass.css and tailwind.config.js. No site needed.
//
//   node tokens.mjs                    enforce
//   node tokens.mjs --update-baseline  re-record accepted collapses

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const BASELINE = join(ROOT, "design", "token-collapse-baseline.json");
const UPDATE = process.argv.includes("--update-baseline");

const css = readFileSync(join(ROOT, "frontend/src/theme/glass.css"), "utf8");
const tw = readFileSync(join(ROOT, "frontend/tailwind.config.js"), "utf8");

// ---------- token values, per theme ----------------------------------------
// glass.css emits :root (light) then a dark block that redeclares only what
// changes, so a theme-constant token is inherited and must fall back.
const [lightSrc, darkSrc = ""] = css.split(/\[data-theme=["']?dark/);
const readAll = (src) => {
	const out = {};
	for (const m of src.matchAll(/--g-([a-z0-9-]+):\s*([^;]+);/g)) out[m[1]] = m[2].trim();
	return out;
};
const light = readAll(lightSrc);
const darkOnly = readAll(darkSrc);
const dark = { ...light, ...darkOnly };

// ---------- 1. role–token binding -------------------------------------------
// Each entry: the Tailwind alias a ROLE resolves through, and the token it must
// land on. Add a row whenever a role's colour is expressed as an alias.
const BINDINGS = [
	{
		role: "primary action fill (bg-accent)",
		block: "accent",
		key: "DEFAULT",
		mustBe: "brand",
		why: "bg-accent painted --accent-ink; eight form submits went dark olive on light",
	},
	{ role: "accent type on light (accent-700)", block: "accent", key: "700", mustBe: "accent-ink", why: "§2.4 forbids brand setting type on light" },
	{ role: "accent type on light (accent-900)", block: "accent", key: "900", mustBe: "accent-ink", why: "§2.4" },
];

function aliasToken(block, key) {
	const start = tw.indexOf(`${block}: {`);
	if (start < 0) return null;
	const body = tw.slice(start, tw.indexOf("}", start));
	const m = body.match(new RegExp(`${key}:\\s*"rgb\\(var\\(--g-([a-z0-9-]+)-rgb\\)`));
	return m ? m[1] : null;
}

const bindingErrors = [];
for (const b of BINDINGS) {
	const actual = aliasToken(b.block, b.key);
	if (actual !== b.mustBe) {
		bindingErrors.push(`  ${b.role}\n      expected --g-${b.mustBe}, got ${actual ? `--g-${actual}` : "nothing"}  (${b.why})`);
	}
}

// ---------- 2. token collapse ------------------------------------------------
// Pairs equal in one theme and different in the other.
const names = Object.keys(light).filter((n) => !n.endsWith("-rgb"));
const collapses = [];
for (let i = 0; i < names.length; i++) {
	for (let j = i + 1; j < names.length; j++) {
		const a = names[i], b = names[j];
		if (!(a in dark) || !(b in dark)) continue;
		const sameLight = light[a] === light[b];
		const sameDark = dark[a] === dark[b];
		if (sameLight !== sameDark) {
			collapses.push(`${a}|${b}|${sameDark ? "dark" : "light"}`);
		}
	}
}
collapses.sort();

if (UPDATE) {
	writeFileSync(BASELINE, JSON.stringify(collapses, null, "\t") + "\n");
	console.log(`[tokens] collapse baseline updated: ${collapses.length} pair(s)`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "tokens", status: "ok", baselined: true })}`);
	process.exit(0);
}

let baseline = [];
if (existsSync(BASELINE)) baseline = JSON.parse(readFileSync(BASELINE, "utf8"));
const known = new Set(baseline);
const fresh = collapses.filter((c) => !known.has(c));

for (const c of collapses) {
	const [a, b, where] = c.split("|");
	console.log(`[tokens] collapse: --g-${a} == --g-${b} in ${where} only${known.has(c) ? "" : "   <- NEW"}`);
}

if (bindingErrors.length) {
	console.log(`[tokens] ROLE–TOKEN BINDING FAILED:\n${bindingErrors.join("\n")}`);
}

const failed = bindingErrors.length || fresh.length;
if (failed) {
	if (fresh.length) console.log(`[tokens] ${fresh.length} NEW token collapse(s) — each is a theme that can hide a swap`);
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "tokens", status: "fail", bindings: bindingErrors.length, newCollapses: fresh.length })}`);
	process.exit(1);
}

console.log(`[tokens] ${BINDINGS.length} role bindings hold, ${collapses.length} known collapse(s), 0 new`);
console.log(`GATE_RESULT ${JSON.stringify({ gate: "tokens", status: "ok", bindings: BINDINGS.length, collapses: collapses.length })}`);
process.exit(0);
