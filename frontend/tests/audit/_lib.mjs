// Shared plumbing for the static audit suite (tests/audit/*.test.mjs).
//
// Every audit here is bench-free: it reads the source tree, the router table
// and the doctype JSON on disk and asserts structural properties that a crash
// in the field taught us to check (15 Sep 2026). Nothing is mounted.
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { parse as parseSfc } from "@vue/compiler-sfc"

export const FRONTEND = resolve(
	dirname(fileURLToPath(import.meta.url)),
	"..",
	".."
)
export const SRC = join(FRONTEND, "src")
export const REPO = resolve(FRONTEND, "..")
export const HRMS_PY = join(REPO, "hrms")

// Every production source file: .vue and .js under src/, tests excluded.
export function sourceFiles(dir = SRC, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__" && entry !== "node_modules")
				sourceFiles(path, out)
		} else if (/\.(vue|js)$/.test(entry) && !/\.test\./.test(entry))
			out.push(path)
	}
	return out.sort()
}

export const rel = (path) => path.slice(FRONTEND.length + 1)

export function read(path) {
	return readFileSync(path, "utf8")
}

// "@/views/Home.vue" → absolute path; "./attendance" → resolved against `from`.
export function resolveImport(spec, from) {
	let base
	if (spec.startsWith("@/")) base = join(SRC, spec.slice(2))
	else if (spec.startsWith(".")) base = resolve(dirname(from), spec)
	else return null // a package
	for (const candidate of [
		base,
		base + ".js",
		base + ".vue",
		join(base, "index.js"),
	]) {
		if (existsSync(candidate) && statSync(candidate).isFile()) return candidate
	}
	return base // missing — callers report it
}

export function sfc(path) {
	const { descriptor, errors } = parseSfc(read(path), { filename: path })
	return { descriptor, errors }
}

// Line number (1-based) of a character offset inside `text`.
export function lineOf(text, offset) {
	let line = 1
	for (let i = 0; i < offset && i < text.length; i++)
		if (text[i] === "\n") line++
	return line
}

// Static and dynamic import specifiers of one file (SFC script blocks included).
export function importsOf(path) {
	const text = path.endsWith(".vue") ? scriptText(path) : read(path)
	const specs = []
	const re =
		/\bimport\s*(?:[\w${},*\s]+?\s*from\s*)?["']([^"']+)["']|\bimport\(\s*["']([^"']+)["']\s*\)/g
	let m
	while ((m = re.exec(text))) specs.push(m[1] || m[2])
	return specs
}

export function scriptText(path) {
	const { descriptor } = sfc(path)
	return [descriptor.scriptSetup?.content, descriptor.script?.content]
		.filter(Boolean)
		.join("\n")
}

export function templateText(path) {
	const { descriptor } = sfc(path)
	return descriptor.template?.content || ""
}

// ---------------------------------------------------------------------------
// Route table, read statically from src/router/*.js. The router imports
// @ionic/vue-router and a .vue shell, so it cannot be imported under node;
// the shape is regular enough to lift with a small parser instead.
// ---------------------------------------------------------------------------
const CONSTANTS = (() => {
	const text = read(join(SRC, "utils", "helpdeskHub.js"))
	const out = {}
	for (const m of text.matchAll(/export const (\w+)\s*=\s*["']([^"']+)["']/g))
		out[m[1]] = m[2]
	return out
})()

function literal(value) {
	if (value === undefined) return undefined
	const v = value.trim()
	const m = v.match(/^["'`]([^"'`]*)["'`]$/)
	if (m) return m[1]
	if (v in CONSTANTS) return CONSTANTS[v]
	return v // an expression — reported as-is
}

function matchBrace(text, open) {
	let depth = 0
	for (let i = open; i < text.length; i++) {
		const c = text[i]
		if (c === "{") depth++
		else if (c === "}") {
			depth--
			if (depth === 0) return i
		} else if (c === '"' || c === "'" || c === "`") {
			i = text.indexOf(c, i + 1)
		} else if (c === "/" && text[i + 1] === "/") {
			i = text.indexOf("\n", i)
		}
	}
	throw new Error("unbalanced brace at " + open)
}

// Lifts { path, name, component, redirect, children } objects out of a router
// module. Object literals are matched brace-balanced so nested `children` and
// `redirect: { path, query }` survive.
export function parseRouteObjects(text) {
	const routes = []
	let i = 0
	while ((i = text.indexOf("{", i)) !== -1) {
		const end = matchBrace(text, i)
		const body = text.slice(i + 1, end)
		const stripped = body.replace(/\/\/[^\n]*/g, "")
		if (/^\s*(?:name|path)\s*:/.test(stripped) && /\bpath\s*:/.test(stripped)) {
			routes.push(routeFromBody(stripped))
			i = end + 1
		} else i++
	}
	return routes
}

function routeFromBody(body) {
	const route = {}
	const childrenAt = body.search(/\bchildren\s*:\s*\[/)
	let own = body
	if (childrenAt !== -1) {
		const start = body.indexOf("[", childrenAt)
		let depth = 0
		let end = start
		for (; end < body.length; end++) {
			if (body[end] === "[") depth++
			else if (body[end] === "]") {
				depth--
				if (depth === 0) break
			}
		}
		const inner = body.slice(start + 1, end)
		route.children = parseRouteObjects(inner)
		route.spreads = [...inner.matchAll(/\.\.\.(\w+)/g)].map((m) => m[1])
		own = body.slice(0, childrenAt) + body.slice(end + 1)
	}
	const pathM = own.match(/\bpath\s*:\s*([^,\n]+)/)
	route.path = literal(pathM?.[1])
	const nameM = own.match(/\bname\s*:\s*([^,\n]+)/)
	route.name = literal(nameM?.[1])
	const compM = own.match(
		/\bcomponent\s*:\s*(?:\(\)\s*=>\s*import\(\s*["']([^"']+)["']\s*\)|(\w+))/
	)
	if (compM) route.component = compM[1] || compM[2]
	const redirM = own.match(/\bredirect\s*:\s*(\{[^}]*\}|[^,\n]+)/)
	if (redirM) {
		const r = redirM[1].trim()
		if (r.startsWith("{")) {
			const p = r.match(/\bpath\s*:\s*([^,}\s]+)/)
			const n = r.match(/\bname\s*:\s*([^,}\s]+)/)
			route.redirect = { path: literal(p?.[1]), name: literal(n?.[1]) }
		} else route.redirect = literal(r)
	}
	route.props = /\bprops\s*:\s*true/.test(own)
	return route
}

// The full table with spreads (…attendanceRoutes) inlined, plus a flat list.
export function routeTable() {
	const routerDir = join(SRC, "router")
	const index = read(join(routerDir, "index.js"))
	const modules = {}
	for (const m of index.matchAll(/import (\w+) from "\.\/(\w+)"/g)) {
		modules[m[1]] = parseRouteObjects(read(join(routerDir, m[2] + ".js")))
	}
	const localImports = {}
	for (const m of index.matchAll(/import (\w+) from "(@\/views\/[^"]+)"/g))
		localImports[m[1]] = m[2]

	const inline = (routes) =>
		routes.map((r) => {
			if (r.children) {
				const expanded = inline(r.children)
				for (const spread of r.spreads || [])
					expanded.push(...inline(modules[spread] || []))
				r.children = expanded
			}
			if (r.component && !r.component.includes("/"))
				r.component = localImports[r.component] || r.component
			return r
		})
	const top = inline(parseRouteObjects(index))
	const flat = []
	const walk = (rs) => {
		for (const r of rs) {
			flat.push(r)
			if (r.children) walk(r.children)
		}
	}
	walk(top)
	return { top, flat }
}
