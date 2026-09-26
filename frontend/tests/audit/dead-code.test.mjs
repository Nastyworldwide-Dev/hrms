// Dead code and dead template references (static audit, 15 Sep 2026).
//
// Owner's brief: "no more gaps, dead pages, dead functions". Three kinds of
// dead are cheap to prove from the tree and expensive to find by hand:
//
//   1. a component or module file nothing imports (a page nobody can reach, a
//      helper that outlived its caller — views are covered in routes.test.mjs)
//   2. an exported symbol no other module imports
//   3. a template that names something the script never defines — a handler
//      on @click, a v-if / v-model source, a component tag that resolves to
//      nothing at runtime (Vue only WARNS in the console and renders nothing
//      or a plain element in its place)
//
// (3) uses @vue/compiler-sfc exactly as the build does: the script's binding
// metadata drives template compilation, so anything that falls back to
// `_ctx.name` is not a setup binding, and anything that needs
// `_resolveComponent` is not an imported component. Both are checked against
// the app's real globals (main.js: app.component / globalProperties).
import { test } from "node:test"
import assert from "node:assert/strict"
import { compileScript, compileTemplate, parse } from "@vue/compiler-sfc"
import { existsSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import {
	FRONTEND,
	SRC,
	read,
	rel,
	resolveImport,
	sourceFiles,
	sfc,
	scriptText,
} from "./_lib.mjs"

const files = sourceFiles()

// every import edge in src/: importer → resolved target path
const edges = []
for (const file of files) {
	const text = file.endsWith(".vue") ? scriptText(file) : read(file)
	for (const m of text.matchAll(
		/\bimport\s*(?:([\w${},*\s]+?)\s*from\s*)?["']([^"']+)["']|\bimport\(\s*["']([^"']+)["']\s*\)/g
	)) {
		const spec = m[2] || m[3]
		const target = resolveImport(spec, file)
		if (target) edges.push({ from: file, to: target, clause: m[1] || "" })
	}
}
const importedFiles = new Set(edges.map((e) => e.to))
// RequestActionSheet loads summary tables by NAME:
//   import(`../components/${field.componentName}.vue`)  (data/config/requestSummaryFields.js)
for (const m of read(`${SRC}/data/config/requestSummaryFields.js`).matchAll(
	/componentName:\s*"(\w+)"/g
))
	importedFiles.add(`${SRC}/components/${m[1]}.vue`)

// Files that are entry points or wired by name rather than by import.
const ENTRY_POINTS = new Set([
	"src/main.js",
	"src/App.vue",
	"src/resourceConfig.js",
	"src/router/index.js",
	"src/views/DesignSpecimen.vue", // dev-only route, pushed in router/index.js under import.meta.env.DEV
	"src/frappeUiLean.js", // every bare "frappe-ui" import resolves here (vite.config.js alias)
	"src/toastIcons.js", // frappe-ui's Toast icon import resolves here (vite.config.js alias)
])

test("every component and module file is imported by something", () => {
	const dead = files
		.filter((f) => !f.includes("/src/views/")) // views: routes.test.mjs
		.filter((f) => !importedFiles.has(f) && !ENTRY_POINTS.has(rel(f)))
		.map(rel)
	assert.deepEqual(dead, [], `never imported:\n${dead.join("\n")}`)
})

// Named exports of every .js module, and whether any OTHER module imports them.
function namedExports(file) {
	const text = read(file)
	const names = []
	for (const m of text.matchAll(
		/^export\s+(?:const|let|function|async function|class)\s+([\w$]+)/gm
	))
		names.push(m[1])
	for (const m of text.matchAll(/^export\s*\{([^}]+)\}/gm))
		for (const part of m[1].split(",")) {
			const name = part
				.trim()
				.split(/\s+as\s+/)
				.pop()
			if (name) names.push(name)
		}
	return names
}

const importedNames = new Map() // target path → Set of names (or "*" / "default")
for (const e of edges) {
	if (!importedNames.has(e.to)) importedNames.set(e.to, new Set())
	const set = importedNames.get(e.to)
	const clause = e.clause.trim()
	if (!clause) continue
	if (clause.includes("*")) set.add("*")
	const braces = clause.match(/\{([^}]*)\}/)
	if (braces)
		for (const part of braces[1].split(",")) {
			const name = part.trim().split(/\s+as\s+/)[0]
			if (name) set.add(name)
		}
	const bare = clause
		.replace(/\{[^}]*\}/, "")
		.replace(/,/g, "")
		.trim()
	if (bare && !bare.startsWith("*")) set.add("default")
}

// Exports that exist for a reason other than an import from src/.
const EXPORT_EXEMPT = {
	"src/utils/geolocation.js": [
		"GEO_DENIED",
		"GEO_INSECURE",
		"GEO_TIMEOUT",
		"GEO_UNAVAILABLE",
		"GEO_UNSUPPORTED",
	], // error codes, matched by value in CheckInPanel
}

// A pure helper exported only so a test can reach it is a legitimate seam;
// the tests are the second consumer the audit accepts.
function testFiles() {
	const out = []
	const walk = (dir) => {
		if (!existsSync(dir)) return
		for (const entry of readdirSync(dir)) {
			const path = join(dir, entry)
			if (statSync(path).isDirectory()) {
				if (entry !== "node_modules") walk(path)
			} else if (
				/\.(test\.(js|mjs)|spec\.js|mjs)$/.test(entry) &&
				!path.includes("/tests/audit/")
			)
				out.push(path)
		}
	}
	walk(join(FRONTEND, "tests"))
	walk(join(FRONTEND, "e2e"))
	walk(SRC)
	return out.filter((f) => /\.test\.|\.spec\.|\/tests\/|\/e2e\//.test(f))
}
const testText = testFiles().map(read).join("\n")

test("every named export is imported by another module or reached by a test", () => {
	const dead = []
	for (const file of files) {
		if (
			!file.endsWith(".js") ||
			file.includes("/src/router/") ||
			rel(file) === "src/main.js" ||
			// reached through the "frappe-ui" alias; checked on its own below
			rel(file) === "src/frappeUiLean.js"
		)
			continue
		const used = importedNames.get(file) || new Set()
		if (used.has("*")) continue
		const exempt = new Set(EXPORT_EXEMPT[rel(file)] || [])
		for (const name of namedExports(file)) {
			if (used.has(name) || exempt.has(name)) continue
			if (new RegExp(`\\b${name}\\b`).test(testText)) continue
			dead.push(`${rel(file)} exports ${name}`)
		}
	}
	assert.deepEqual(dead, [], `exported but never imported:\n${dead.join("\n")}`)
})

// src/frappeUiLean.js is what every bare "frappe-ui" import resolves to
// (vite.config.js alias). Each name it re-exports must be one src/ imports
// from "frappe-ui", and each name src/ imports must be there — or the build
// quietly grows back to the whole library, or fails on a missing export.
test("the lean frappe-ui entry exports exactly what the app imports from frappe-ui", () => {
	const lean = read(`${SRC}/frappeUiLean.js`)
	const offered = new Set()
	for (const m of lean.matchAll(/^export\s*\{([^}]+)\}/gm))
		for (const part of m[1].split(",")) offered.add(part.trim().split(/\s+as\s+/).pop())
	const wanted = new Set()
	for (const file of files)
		for (const m of read(file).matchAll(/import\s*\{([^}]+)\}\s*from\s*"frappe-ui"/g))
			for (const part of m[1].split(","))
				if (part.trim()) wanted.add(part.trim().split(/\s+as\s+/)[0])
	const missing = [...wanted].filter((n) => !offered.has(n)).sort()
	const unused = [...offered].filter((n) => !wanted.has(n)).sort()
	assert.deepEqual(missing, [], "imported from frappe-ui but not in frappeUiLean.js")
	assert.deepEqual(unused, [], "in frappeUiLean.js but never imported")
})

// ---------------------------------------------------------------------------
// Templates: every identifier and component tag resolves
// ---------------------------------------------------------------------------
const main = read(`${SRC}/main.js`)
const GLOBAL_COMPONENTS = new Set([
	...[...main.matchAll(/app\.component\("(\w+)"/g)].map((m) => m[1]),
	"router-link",
	"RouterLink",
	"router-view",
	"RouterView",
])
// $slots/$emit/$attrs/$props are the component proxy; `__` is the translation
// global registered by plugins/translationsPlugin.js
const GLOBAL_PROPERTIES = new Set([
	"$slots",
	"$emit",
	"$attrs",
	"$props",
	"$el",
	"$refs",
	"$nextTick",
	"$forceUpdate",
	"__",
])

test("every template identifier and component tag resolves to a binding, a global or an import", () => {
	const findings = []
	for (const file of files) {
		if (!file.endsWith(".vue")) continue
		const { descriptor } = sfc(file)
		if (!descriptor.template) continue
		let bindings = {}
		if (descriptor.scriptSetup || descriptor.script)
			bindings = compileScript(descriptor, { id: "audit" }).bindings || {}
		const tpl = compileTemplate({
			source: descriptor.template.content,
			filename: file,
			id: "audit",
			compilerOptions: { bindingMetadata: bindings },
		})
		for (const err of tpl.errors)
			findings.push(`${rel(file)}: template error — ${err.message || err}`)
		for (const m of tpl.code.matchAll(/_ctx\.([A-Za-z_$][\w$]*)/g)) {
			if (!GLOBAL_PROPERTIES.has(m[1]))
				findings.push(
					`${rel(file)}: template uses \`${
						m[1]
					}\` which the script never defines`
				)
		}
		for (const m of tpl.code.matchAll(/_resolveComponent\("([^"]+)"/g)) {
			if (!GLOBAL_COMPONENTS.has(m[1]))
				findings.push(
					`${rel(file)}: component <${
						m[1]
					}> is neither imported nor registered globally`
				)
		}
		for (const m of tpl.code.matchAll(/_resolveDirective\("([^"]+)"/g))
			findings.push(`${rel(file)}: directive v-${m[1]} is not registered`)
	}
	assert.deepEqual([...new Set(findings)], [], findings.join("\n"))
})

test("the template check catches an undefined handler and an unimported component", () => {
	const source = `<template><Foo @click="go" /><div v-if="flag">{{ label }}</div></template>
<script setup>
import { ref } from "vue"
const label = ref("x")
</script>`
	const { descriptor } = parse(source, { filename: "t.vue" })
	const bindings = compileScript(descriptor, { id: "t" }).bindings
	const tpl = compileTemplate({
		source: descriptor.template.content,
		filename: "t.vue",
		id: "t",
		compilerOptions: { bindingMetadata: bindings },
	})
	const ctx = [...tpl.code.matchAll(/_ctx\.(\w+)/g)].map((m) => m[1])
	assert.deepEqual([...new Set(ctx)].sort(), ["flag", "go"])
	assert.match(tpl.code, /_resolveComponent\("Foo"\)/)
})
