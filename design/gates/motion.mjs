// Gate 10 — MOTION: durations come from the scale, and the preference is
// honoured app-wide (revamp §19, WCAG 2.3.3).
//
// Measured 22 Sep 2026 before this existed:
//   prefers-reduced-motion was honoured in FOUR components out of about
//   ninety — the skeleton shimmer, the pending bar, and the offline and update
//   banners. Everything else animated regardless of the setting.
//
//   And SopFormSheet referenced `--motion-glide` four times. That variable has
//   been defined nowhere since the Modernist stylesheet was removed, so those
//   transitions were DEAD: the toggle simply snapped, and nothing reported it,
//   because an undefined custom property makes a declaration invalid and CSS
//   drops invalid declarations in silence.
//
// The second one is why this gate checks for undefined variables rather than
// only for raw numbers. A hand-written `200ms` is untidy; a reference to a
// variable that does not exist is a feature that is not there at all.
//
// Static — reads the theme CSS and every .vue under src. No site needed.
//
//   node motion.mjs

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))));
const SRC = join(ROOT, "frontend/src");
const THEME = join(SRC, "theme");

// Comments are BLANKED, never stripped: a comment explaining a rule must not
// be counted as the thing the rule forbids. Six gates in this repo have been
// caught by their own prose.
const decomment = (text) =>
	text
		.split(/(\/\*[\s\S]*?\*\/)/)
		.filter((part) => !part.startsWith("/*"))
		.join("")
		.split(/(<!--[\s\S]*?-->)/)
		.filter((part) => !part.startsWith("<!--"))
		.join("");

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry);
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__" && entry !== "node_modules") walk(path, out);
		} else if (/\.(vue|css)$/.test(entry)) out.push(path);
	}
	return out;
}

const FILES = walk(SRC);
const source = new Map(FILES.map((f) => [f, readFileSync(f, "utf8")]));

// ---------- 1. every --g-* motion reference resolves --------------------------
const themeCss = readdirSync(THEME)
	.filter((f) => f.endsWith(".css"))
	.map((f) => readFileSync(join(THEME, f), "utf8"))
	.join("\n");
const defined = new Set([...themeCss.matchAll(/^\s*(--[a-z0-9-]+):/gm)].map((m) => m[1]));

const undefinedVars = [];
for (const [file, text] of source) {
	for (const m of decomment(text).matchAll(/var\(\s*(--[a-z0-9-]+)\s*\)/g)) {
		// Only OUR namespace. Ionic and frappe-ui define their own elsewhere.
		if (!m[1].startsWith("--g-") && !m[1].startsWith("--motion")) continue;
		if (defined.has(m[1])) continue;
		undefinedVars.push(`  ${relative(ROOT, file)}: var(${m[1]}) is defined nowhere — the declaration is dropped`);
	}
}

// ---------- 2. durations come from the scale ---------------------------------
const rawDurations = [];
for (const [file, text] of source) {
	if (file.startsWith(THEME) && /glass\.(css|variables\.css)$/.test(file)) continue; // generated
	for (const m of decomment(text).matchAll(/(transition|animation)(-duration)?:\s*([^;"']+)/g)) {
		const value = m[3];
		if (/var\(--g-motion-/.test(value)) continue;
		if (/^\s*(none|inherit|initial|unset)\s*$/.test(value)) continue;
		if (!/\d+m?s/.test(value)) continue;
		// The reduced-motion override IS the rule this gate enforces, so
		// counting it would make the gate fail on its own fix — the same
		// self-tripping shape that caught lint, usage and four tests today.
		if (/!important/.test(m[0])) continue;
		rawDurations.push(`  ${relative(ROOT, file)}: ${m[0].trim().slice(0, 80)}`);
	}
}

// ---------- 3. the preference is honoured app-wide ---------------------------
const components = readFileSync(join(THEME, "glass-components.css"), "utf8");
const blanket = /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\*,/.test(components);
const preference = blanket
	? []
	: ["  no app-wide @media (prefers-reduced-motion: reduce) block — per-component coverage was 4 of ~90"];

// `transition: none` cancels a transition mid-flight, so Vue's <Transition>
// never hears transitionend and can strand an element in its enter-from state.
const zeroed = blanket && /transition-duration:\s*0m?s\s*!important/.test(components)
	? ["  the app-wide block uses 0ms; use 1ms so transitionend still fires"]
	: [];

//: A LOOPING AMBIENT animation is not an interaction transition. It has no
//: business on the 50-600ms interaction scale — a 2.4s locator ring pulses at
//: the speed of a heartbeat on purpose — and the app-wide reduced-motion block
//: stops it outright for anyone who asked. Named individually so a new one has
//: to be argued for rather than absorbed.
const AMBIENT = new Set(["user-pin-pulse", "g-pin-ring"]);
const scaled = rawDurations.filter((line) => ![...AMBIENT].some((name) => line.includes(name)));

const problems = [
	["motion variables that resolve to nothing", undefinedVars],
	["durations outside the motion scale", scaled],
	["reduced-motion coverage", preference],
	["reduced-motion implementation", zeroed],
].filter(([, list]) => list.length);

for (const [what, list] of problems) {
	console.log(`[motion] ${list.length} ${what}:`);
	for (const line of list) console.log(line);
}

if (problems.length) {
	console.log(`GATE_RESULT ${JSON.stringify({ gate: "motion", status: "fail", undefinedVars: undefinedVars.length, raw: scaled.length })}`);
	process.exit(1);
}

console.log(`[motion] OK — every motion variable resolves, durations come from the scale, reduced motion honoured app-wide`);
console.log(`GATE_RESULT ${JSON.stringify({ gate: "motion", status: "ok", files: FILES.length })}`);
process.exit(0);
