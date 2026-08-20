// Compiles design/tokens.json (the single palette source of truth) into:
//   frontend/src/theme/glass.css            — --g-* custom properties
//   frontend/src/theme/glass.tailwind.cjs   — Tailwind theme fragment
//   frontend/src/theme/glass.variables.css  — Ionic --ion-* variables
// Run: yarn tokens (from frontend/). Deterministic: sorted keys, byte-identical reruns.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const SRC = join(ROOT, "design", "tokens.json");
const OUT_DIR = join(ROOT, "frontend", "src", "theme");

const HEADER =
	"GENERATED FROM design/tokens.json BY design/build-tokens.mjs — DO NOT EDIT BY HAND.\n" +
	"   Regenerate: yarn tokens  (in frontend/)";

// ---------- load + validate (fail loudly) ----------

const errors = [];
const bad = (path, msg) => errors.push(`  ${path}: ${msg}`);

let tokens;
try {
	tokens = JSON.parse(readFileSync(SRC, "utf8"));
} catch (e) {
	console.error(`[build-tokens] Cannot read ${SRC}: ${e.message}`);
	process.exit(1);
}

const isHex = (v) => typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v);
const isVal = (v) => (typeof v === "string" && v.trim() !== "") || typeof v === "number";
const sorted = (obj) => Object.keys(obj).sort();

for (const group of ["color-constant", "color-themed", "color-semantic", "spacing", "radius", "blur", "shadow", "type", "motion"]) {
	if (!tokens[group] || typeof tokens[group] !== "object") bad(group, "missing group");
}
if (errors.length) die();

for (const name of sorted(tokens["color-constant"])) {
	if (!isVal(tokens["color-constant"][name].value)) bad(`color-constant.${name}`, "value must be a non-empty string");
}
for (const group of ["color-themed", "color-semantic"]) {
	for (const name of sorted(tokens[group])) {
		const v = tokens[group][name].value;
		if (typeof v !== "object" || !isVal(v?.light) || !isVal(v?.dark))
			bad(`${group}.${name}`, "value must be { light, dark }");
	}
}
for (const group of ["spacing", "radius", "blur", "shadow"]) {
	for (const name of sorted(tokens[group])) {
		if (!isVal(tokens[group][name].value)) bad(`${group}.${name}`, "value must be a non-empty string");
	}
}
if (typeof tokens.type.family !== "object") bad("type.family", "missing");
if (typeof tokens.type.scale !== "object") bad("type.scale", "missing");
if (errors.length) die();
for (const name of sorted(tokens.type.family)) {
	if (!isVal(tokens.type.family[name].value)) bad(`type.family.${name}`, "value must be a non-empty string");
}
for (const name of sorted(tokens.type.scale)) {
	const s = tokens.type.scale[name];
	for (const field of ["family", "size", "weight", "tracking", "line-height"]) {
		if (!isVal(s[field])) bad(`type.scale.${name}`, `missing ${field}`);
	}
	if (s.family && !tokens.type.family[s.family]) bad(`type.scale.${name}`, `unknown family "${s.family}"`);
}
for (const name of sorted(tokens.motion)) {
	if (!isVal(tokens.motion[name].duration)) bad(`motion.${name}`, "missing duration");
}
if (errors.length) die();

function die() {
	console.error(`[build-tokens] design/tokens.json is invalid:\n${errors.join("\n")}`);
	process.exit(1);
}

// ---------- helpers ----------

const triplet = (hex) =>
	[1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(" ");

const decl = (name, value) => `\t--g-${name}: ${value};`;

// base prop, then -rgb for hex values (opacity-modifier support in Tailwind)
function colorDecls(name, value) {
	const out = [decl(name, value)];
	if (isHex(value)) out.push(decl(`${name}-rgb`, triplet(value)));
	return out;
}

// ---------- OUTPUT 1: glass.css ----------

const light = [];
const dark = [];

light.push("\t/* color-constant */");
for (const name of sorted(tokens["color-constant"]))
	light.push(...colorDecls(name, tokens["color-constant"][name].value));

for (const group of ["color-themed", "color-semantic"]) {
	light.push(`\t/* ${group} (light) */`);
	dark.push(`\t/* ${group} (dark) */`);
	for (const name of sorted(tokens[group])) {
		const v = tokens[group][name].value;
		// -rgb only when both themes are hex, so the var exists in every theme
		const withRgb = isHex(v.light) && isHex(v.dark);
		light.push(...(withRgb ? colorDecls(name, v.light) : [decl(name, v.light)]));
		dark.push(...(withRgb ? colorDecls(name, v.dark) : [decl(name, v.dark)]));
	}
}

for (const group of ["spacing", "radius", "blur", "shadow"]) {
	light.push(`\t/* ${group} */`);
	// shadow token names get the group prefix (--g-shadow-action); the others
	// already carry theirs (radius-panel, blur-ghost) or read fine bare
	for (const name of sorted(tokens[group]))
		light.push(decl(group === "shadow" ? `shadow-${name}` : name, tokens[group][name].value));
}

light.push("\t/* type */");
for (const name of sorted(tokens.type.family)) light.push(decl(`font-${name}`, tokens.type.family[name].value));
for (const name of sorted(tokens.type.scale)) {
	const s = tokens.type.scale[name];
	light.push(decl(`type-${name}-family`, `var(--g-font-${s.family})`));
	light.push(decl(`type-${name}-line-height`, s["line-height"]));
	light.push(decl(`type-${name}-size`, s.size));
	light.push(decl(`type-${name}-tracking`, s.tracking));
	light.push(decl(`type-${name}-weight`, s.weight));
}

// motion: `property` and `iteration: one-shot` are documentation, not CSS values — not emitted
light.push("\t/* motion */");
for (const name of sorted(tokens.motion)) {
	const m = tokens.motion[name];
	light.push(decl(`motion-${name}-duration`, m.duration));
	if (m.easing) light.push(decl(`motion-${name}-easing`, m.easing));
	if (m.iteration === "infinite") light.push(decl(`motion-${name}-iteration`, m.iteration));
}

const glassCss = `/* ${HEADER} */

:root {
${light.join("\n")}
}

html[data-theme="dark"] {
${dark.join("\n")}
}
`;

// ---------- OUTPUT 2: glass.tailwind.cjs ----------

// token name → semantic utility name (only where the raw name reads badly)
const RENAME = {
	"glass-fill": "glass",
	"glass-fill-fallback": "glass-fallback",
	"glass-rim": "rim",
	ink2: "ink-2",
	ink3: "ink-3",
};
const NON_COLOR_THEMED = new Set(["lift", "blob-opacity"]); // shadow / opacity, mapped below

const colors = {};
const nonTriplet = []; // rgba()-based tokens: plain var(), no opacity modifier — reported
function addColor(name, value) {
	const key = RENAME[name] ?? name;
	if (isHex(value)) {
		colors[key] = `rgb(var(--g-${name}-rgb) / <alpha-value>)`;
	} else {
		colors[key] = `var(--g-${name})`;
		nonTriplet.push(name);
	}
}
for (const name of sorted(tokens["color-constant"])) addColor(name, tokens["color-constant"][name].value);
for (const group of ["color-themed", "color-semantic"]) {
	for (const name of sorted(tokens[group])) {
		if (NON_COLOR_THEMED.has(name)) continue;
		const v = tokens[group][name].value;
		// triplet only when both themes are hex; otherwise plain var()
		addColor(name, isHex(v.light) && isHex(v.dark) ? v.light : String(v.light));
	}
}

const borderRadius = {};
for (const name of sorted(tokens.radius)) borderRadius[name.replace(/^radius-/, "")] = `var(--g-${name})`;

const backdropBlur = {};
for (const name of sorted(tokens.blur)) backdropBlur[name.replace(/^blur-/, "")] = `var(--g-${name})`;

const spacing = {};
const multiValueSpacing = []; // two-value shorthands can't be Tailwind spacing entries — reported
for (const name of sorted(tokens.spacing)) {
	if (tokens.spacing[name].value.trim().includes(" ")) multiValueSpacing.push(name);
	else spacing[name] = `var(--g-${name})`;
}

const fontFamily = {};
for (const name of sorted(tokens.type.family)) fontFamily[name] = `var(--g-font-${name})`;

const fontSize = {};
for (const name of sorted(tokens.type.scale)) {
	const s = tokens.type.scale[name];
	fontSize[name] = [s.size, { fontWeight: String(s.weight), letterSpacing: s.tracking, lineHeight: String(s["line-height"]) }];
}

const transitionDuration = {};
const transitionTimingFunction = {};
for (const name of sorted(tokens.motion)) {
	transitionDuration[name] = `var(--g-motion-${name}-duration)`;
	if (tokens.motion[name].easing) transitionTimingFunction[name] = `var(--g-motion-${name}-easing)`;
}

const boxShadow = { lift: "var(--g-lift)" };
for (const name of sorted(tokens.shadow)) boxShadow[name] = `var(--g-shadow-${name})`;

const fragment = {
	backdropBlur,
	borderRadius,
	boxShadow,
	colors,
	fontFamily,
	fontSize,
	opacity: { blob: "var(--g-blob-opacity)" },
	spacing,
	transitionDuration,
	transitionTimingFunction,
};

function cjs(value, depth) {
	if (Array.isArray(value)) return `[${value.map((v) => cjs(v, depth)).join(", ")}]`;
	if (value && typeof value === "object") {
		const ind = "\t".repeat(depth + 1);
		const body = sorted(value)
			.map((k) => `${ind}${/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(k) ? k : JSON.stringify(k)}: ${cjs(value[k], depth + 1)},`)
			.join("\n");
		return `{\n${body}\n${"\t".repeat(depth)}}`;
	}
	return JSON.stringify(value);
}

const glassTailwind = `// ${HEADER.replace("\n   ", "\n// ")}
// Merge into tailwind.config.js theme.extend (prompt 1.3).
// rgba()-based tokens (${nonTriplet.map((n) => RENAME[n] ?? n).join(", ")})
// are plain var() references and do not support Tailwind opacity modifiers.
module.exports = ${cjs(fragment, 0)};
`;

// ---------- OUTPUT 3: glass.variables.css ----------

// Only the --ion-* variables theme/variables.css sets today and that a glass
// token actually covers. Literal values: this file must stand alone.
const themed = (name) => tokens["color-themed"][name].value;
const ionMap = {
	"--ion-background-color": themed("bg"),
	"--ion-font-family": { light: tokens.type.family.ui.value, dark: tokens.type.family.ui.value },
	"--ion-tab-bar-background-focused": themed("icon-bg"),
	"--ion-tab-bar-color-selected": themed("accent-ink"),
	"--ion-text-color": themed("ink"),
};
const ionBlock = (theme) =>
	sorted(ionMap)
		.map((k) => `\t${k}: ${ionMap[k][theme]};`)
		.join("\n");

const glassVariables = `/* ${HEADER} */

/* Ionic variables mapped from glass tokens. The --ion-color-* palettes
   (primary, secondary, …) in theme/variables.css have no glass equivalents
   and are deliberately not generated here. */

:root {
${ionBlock("light")}
}

html[data-theme="dark"] {
${ionBlock("dark")}
}
`;

// ---------- write ----------

const outputs = {
	"glass.css": glassCss,
	"glass.tailwind.cjs": glassTailwind,
	"glass.variables.css": glassVariables,
};
for (const file of sorted(outputs)) {
	writeFileSync(join(OUT_DIR, file), outputs[file]);
	console.log(`[build-tokens] wrote frontend/src/theme/${file} (${outputs[file].length} bytes)`);
}
console.log(
	`[build-tokens] no opacity modifiers (rgba tokens): ${nonTriplet.join(", ")}; ` +
		`not in Tailwind spacing (two-value): ${multiValueSpacing.join(", ")}`
);
