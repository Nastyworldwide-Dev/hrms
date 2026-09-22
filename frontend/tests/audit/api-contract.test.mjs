// API contract (static audit, 15 Sep 2026).
//
// Every request the PWA makes names a Python function by string —
// `url: "hrms.api.get_leave_types"` — and passes its arguments as an object.
// Nothing checks that string against the backend: a renamed method, a new
// required parameter or a misspelt kwarg all surface as "Could not load" on a
// phone, weeks later. This lifts every createResource / createListResource /
// createDocumentResource / call() in src/ (with its static params, makeParams
// and every .submit({...}) / .fetch({...}) it is given), parses every
// @frappe.whitelist def under hrms/ for its signature, and asserts:
//
//   - the method exists (hrms.* resolves to a whitelisted def; hrms.api.X
//     honours names imported into hrms/api/__init__.py; core methods are on a
//     named allowlist)
//   - every required positional parameter is supplied, when the PWA's
//     arguments can be read statically
//   - no kwarg is passed that the def does not accept
//   - every field a createListResource reads exists on the doctype
//     (doctype JSON + hrms custom fields + Frappe's standard columns)
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { babelParse } from "@vue/compiler-sfc"
import {
	HRMS_PY,
	REPO,
	read,
	rel,
	resolveImport,
	sourceFiles,
	lineOf,
	sfc,
} from "./_lib.mjs"

// ---------------------------------------------------------------------------
// Backend: every whitelisted def under hrms/ with its parameters
// ---------------------------------------------------------------------------
function pyFiles(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (!["node_modules", "__pycache__", "frontend"].includes(entry))
				pyFiles(path, out)
		} else if (entry.endsWith(".py") && !entry.startsWith("test_"))
			out.push(path)
	}
	return out
}

function splitTopLevel(text) {
	const parts = []
	let depth = 0
	let current = ""
	for (const c of text) {
		if ("([{".includes(c)) depth++
		else if (")]}".includes(c)) depth--
		if (c === "," && depth === 0) {
			parts.push(current)
			current = ""
		} else current += c
	}
	if (current.trim()) parts.push(current)
	return parts.map((p) => p.trim()).filter(Boolean)
}

function parseSignature(paramText) {
	const sig = { required: [], optional: [], varkw: false }
	for (const raw of splitTopLevel(paramText)) {
		if (raw === "*" || raw === "/") continue
		if (raw.startsWith("**")) {
			sig.varkw = true
			continue
		}
		if (raw.startsWith("*")) continue
		// name[: annotation][= default] — the annotation may itself hold "="
		// only inside brackets, which splitTopLevel already protected
		const name = raw.match(/^(\w+)/)[1]
		const hasDefault = /^\w+\s*(?::[^=]*)?=/.test(
			raw.replace(/\[[^\]]*\]/g, "")
		)
		;(hasDefault ? sig.optional : sig.required).push(name)
	}
	return sig
}

export function whitelistedMethods() {
	const methods = new Map()
	const DEF_RE =
		/@frappe\.whitelist\([^)]*\)\s*\n(?:@[^\n]*\n)*\s*def\s+(\w+)\s*\(([^)]*(?:\([^)]*\)[^)]*)*)\)/g
	for (const file of pyFiles(HRMS_PY)) {
		const text = readFileSync(file, "utf8")
		const module = file
			.slice(REPO.length + 1, -3)
			.replace(/\//g, ".")
			.replace(/\.__init__$/, "")
		for (const m of text.matchAll(DEF_RE))
			methods.set(`${module}.${m[1]}`, parseSignature(m[2]))
	}
	// names imported into a package __init__ are reachable through the package
	const init = readFileSync(join(HRMS_PY, "api", "__init__.py"), "utf8")
	for (const m of init.matchAll(
		/^from\s+(hrms\.[\w.]+)\s+import\s+\(?([^)\n]+(?:\n[^)]+)*)\)?/gm
	)) {
		for (const name of m[2]
			.split(",")
			.map((s) =>
				s
					.trim()
					.split(/\s+as\s+/)
					.pop()
			)
			.filter(Boolean)) {
			const target = `${m[1]}.${name}`
			if (methods.has(target))
				methods.set(`hrms.api.${name}`, methods.get(target))
		}
	}
	return methods
}

// Frappe / ERPNext methods the PWA may call. Signatures from frappe v15/v16
// (frappe/client.py, handler.py, core/doctype/user/user.py,
// push_notification.py, desk/search.py). Anything not listed here and not
// under hrms.* fails — add it here with its signature when a new core call
// is introduced, so the contract stays explicit.
const CORE = {
	login: {
		required: [],
		optional: ["usr", "pwd", "tmp_id", "otp", "cmd"],
		varkw: true,
	},
	logout: { required: [], optional: [], varkw: true },
	upload_file: { required: [], optional: [], varkw: true },
	"frappe.client.get_list": {
		required: ["doctype"],
		optional: [
			"fields",
			"filters",
			"group_by",
			"order_by",
			"limit_start",
			"limit_page_length",
			"parent",
			"debug",
			"as_dict",
			"or_filters",
		],
		varkw: false,
	},
	"frappe.client.get": {
		required: ["doctype"],
		optional: ["name", "filters", "parent"],
		varkw: false,
	},
	"frappe.client.get_value": {
		required: ["doctype", "fieldname"],
		optional: ["filters", "as_dict", "debug", "parent"],
		varkw: false,
	},
	"frappe.client.set_value": {
		required: ["doctype", "name", "fieldname"],
		optional: ["value"],
		varkw: false,
	},
	"frappe.client.insert": { required: [], optional: ["doc"], varkw: false },
	"frappe.client.save": { required: ["doc"], optional: [], varkw: false },
	"frappe.client.submit": { required: ["doc"], optional: [], varkw: false },
	"frappe.client.cancel": {
		required: ["doctype", "name"],
		optional: [],
		varkw: false,
	},
	"frappe.client.delete": {
		required: ["doctype", "name"],
		optional: [],
		varkw: false,
	},
	"frappe.client.has_permission": {
		required: ["doctype", "docname"],
		optional: ["perm_type"],
		varkw: false,
	},
	"frappe.client.get_doc_permissions": {
		required: ["doctype", "docname"],
		optional: [],
		varkw: false,
	},
	"frappe.desk.search.search_link": {
		required: ["doctype", "txt"],
		optional: [
			"query",
			"filters",
			"page_length",
			"searchfield",
			"reference_doctype",
			"ignore_user_permissions",
		],
		varkw: false,
	},
	"frappe.core.doctype.user.user.reset_password": {
		required: ["user"],
		optional: [],
		varkw: false,
	},
	"frappe.core.doctype.user.user.update_password": {
		required: ["new_password"],
		optional: ["logout_all_sessions", "key", "old_password"],
		varkw: false,
	},
	"frappe.push_notification.subscribe": {
		required: ["fcm_token", "project_name"],
		optional: [],
		varkw: false,
	},
	"frappe.push_notification.unsubscribe": {
		required: ["fcm_token", "project_name"],
		optional: [],
		varkw: false,
	},
	"frappe.translate.get_all_translations": {
		required: [],
		optional: ["lang"],
		varkw: false,
	},
	// reads frappe.form_dict itself
	"frappe.desk.reportview.get": { required: [], optional: [], varkw: true },
	"frappe.model.workflow.get_transitions": {
		required: ["doc"],
		optional: ["workflow", "raise_exception"],
		varkw: false,
	},
	"frappe.model.workflow.apply_workflow": {
		required: ["doc", "action"],
		optional: [],
		varkw: false,
	},
	"frappe.realtime.get_user_info": { required: [], optional: [], varkw: false },
}

// ---------------------------------------------------------------------------
// Frontend: every request site with its statically visible arguments
// ---------------------------------------------------------------------------
const RESOURCE_FACTORIES = new Set([
	"createResource",
	"createListResource",
	"createDocumentResource",
])

function objectKeys(node, scope) {
	// returns { keys: Set, dynamic: bool } for an ObjectExpression
	const keys = new Set()
	let dynamic = false
	if (!node) return { keys, dynamic: true }
	if (node.type !== "ObjectExpression") return { keys, dynamic: true }
	for (const p of node.properties) {
		if (p.type === "SpreadElement") {
			const inner =
				p.argument.type === "CallExpression" &&
				p.argument.callee.type === "Identifier"
					? scope.fns.get(p.argument.callee.name)
					: null
			if (inner) {
				for (const k of inner.keys) keys.add(k)
				dynamic = dynamic || inner.dynamic
			} else dynamic = true
		} else if (p.key?.type === "Identifier" && !p.computed) keys.add(p.key.name)
		else if (p.key?.type === "StringLiteral") keys.add(p.key.value)
		else dynamic = true
	}
	return { keys, dynamic }
}

// The object a function returns, when it is a plain `return {...}` / `=> ({...})`.
function returnedObject(fn, scope) {
	if (!fn) return { keys: new Set(), dynamic: true }
	if (fn.type === "Identifier")
		return scope.fns.get(fn.name) || { keys: new Set(), dynamic: true }
	if (
		fn.type !== "ArrowFunctionExpression" &&
		fn.type !== "FunctionExpression" &&
		fn.type !== "ObjectMethod"
	)
		return { keys: new Set(), dynamic: true }
	if (fn.body.type === "ObjectExpression") return objectKeys(fn.body, scope)
	if (fn.body.type === "BlockStatement") {
		const ret = fn.body.body.find((s) => s.type === "ReturnStatement")
		if (ret?.argument?.type === "ObjectExpression")
			return objectKeys(ret.argument, scope)
	}
	return { keys: new Set(), dynamic: true }
}

function literalString(node, scope) {
	if (!node) return null
	if (node.type === "StringLiteral") return node.value
	if (node.type === "TemplateLiteral" && node.expressions.length === 0)
		return node.quasis[0].value.cooked
	if (node.type === "Identifier" && scope.consts.has(node.name))
		return scope.consts.get(node.name)
	return null
}

function walk(node, visit, parent = null) {
	if (!node || typeof node.type !== "string") return
	visit(node, parent)
	for (const key of Object.keys(node)) {
		if (key === "loc") continue
		const child = node[key]
		if (Array.isArray(child))
			child.forEach(
				(c) => c && typeof c.type === "string" && walk(c, visit, node)
			)
		else if (child && typeof child.type === "string") walk(child, visit, node)
	}
}

export function requestSites(code, file, lineOffset = 0, absPath = null) {
	const ast = babelParse(code, { sourceType: "module", plugins: ["jsx"] })
	const scope = { consts: new Map(), fns: new Map() }
	const imports = new Map() // local name → import specifier
	for (const stmt of ast.program.body) {
		if (stmt.type === "ImportDeclaration") {
			for (const sp of stmt.specifiers)
				imports.set(sp.local.name, stmt.source.value)
			continue
		}
		const decl =
			stmt.type === "ExportNamedDeclaration" ? stmt.declaration : stmt
		if (decl?.type !== "VariableDeclaration") continue
		for (const d of decl.declarations) {
			if (d.id.type !== "Identifier") continue
			if (d.init?.type === "StringLiteral")
				scope.consts.set(d.id.name, d.init.value)
			if (
				d.init?.type === "ArrowFunctionExpression" ||
				d.init?.type === "FunctionExpression"
			)
				scope.fns.set(d.id.name, returnedObject(d.init, scope))
		}
	}
	const sites = []
	const byVar = new Map()
	const byNode = new Map()
	const exportedNames = new Set()
	for (const stmt of ast.program.body) {
		if (
			stmt.type === "ExportNamedDeclaration" &&
			stmt.declaration?.type === "VariableDeclaration"
		)
			for (const d of stmt.declaration.declarations)
				if (d.id.type === "Identifier") exportedNames.add(d.id.name)
	}
	walk(ast.program, (node, parent) => {
		if (node.type !== "CallExpression") return
		const callee = node.callee
		const name =
			callee.type === "Identifier"
				? callee.name
				: callee.type === "MemberExpression"
				? callee.property?.name
				: null
		// call("login", {...})
		if (name === "call" && callee.type === "Identifier" && node.arguments[0]) {
			const url = literalString(node.arguments[0], scope)
			const args = objectKeys(node.arguments[1], scope)
			sites.push({
				file,
				absPath,
				line: lineOffset + lineOf(code, node.start),
				url,
				kind: "call",
				...args,
				doctype: null,
				fields: [],
			})
			return
		}
		if (
			!RESOURCE_FACTORIES.has(name) ||
			node.arguments[0]?.type !== "ObjectExpression"
		)
			return
		const opts = node.arguments[0]
		const prop = (k) =>
			opts.properties.find(
				(p) => p.key && !p.computed && (p.key.name === k || p.key.value === k)
			)
		const urlNode = prop("url")
		const site = {
			file,
			absPath,
			line: lineOffset + lineOf(code, node.start),
			kind: name,
			url: urlNode ? literalString(urlNode.value, scope) : null,
			urlDynamic:
				Boolean(urlNode) && literalString(urlNode.value, scope) === null,
			keys: new Set(),
			dynamic: false,
			// with makeParams, submit()/fetch() arguments are INPUTS to makeParams,
			// not kwargs — unless makeParams just hands them through
			argsAreKwargs: true,
			doctype: prop("doctype")
				? literalString(prop("doctype").value, scope)
				: null,
			fields: [],
			varName: null,
			exported: false,
		}
		const params = prop("params")
		if (params) {
			const r = objectKeys(params.value, scope)
			for (const k of r.keys) site.keys.add(k)
			site.dynamic = site.dynamic || r.dynamic
		}
		const make = prop("makeParams")
		if (make) {
			const fn = make.type === "ObjectMethod" ? make : make.value
			const passthrough =
				fn?.body?.type === "BlockStatement" &&
				fn.params[0]?.type === "Identifier" &&
				fn.body.body.some(
					(s) =>
						s.type === "ReturnStatement" &&
						s.argument?.type === "Identifier" &&
						s.argument.name === fn.params[0].name
				)
			if (passthrough) site.argsAreKwargs = true
			else {
				site.argsAreKwargs = false
				const r = returnedObject(fn, scope)
				for (const k of r.keys) site.keys.add(k)
				site.dynamic = site.dynamic || r.dynamic
			}
		}
		const fields = prop("fields")
		if (fields?.value?.type === "ArrayExpression")
			site.fields = fields.value.elements.map((e) =>
				e?.type === "StringLiteral" ? e.value : null
			)
		if (
			parent?.type === "VariableDeclarator" &&
			parent.id.type === "Identifier"
		) {
			site.varName = parent.id.name
			site.exported = exportedNames.has(parent.id.name)
			byVar.set(parent.id.name, site)
		}
		byNode.set(node, site)
		sites.push(site)
	})
	// x.submit({...}) / x.fetch({...}) / x.reload({...}) / createResource({...}).submit({...})
	const calls = [] // { name, spec, keys, dynamic } for names bound by import
	walk(ast.program, (node) => {
		if (
			node.type !== "CallExpression" ||
			node.callee.type !== "MemberExpression"
		)
			return
		const method = node.callee.property?.name
		if (
			!["submit", "fetch", "reload"].includes(method) ||
			!node.arguments.length
		)
			return
		let obj = node.callee.object
		if (obj.type === "MemberExpression" && obj.object.type === "Identifier")
			obj = obj.object // docList.insert.submit()
		const r = objectKeys(node.arguments[0], scope)
		let site = null
		if (obj.type === "CallExpression") site = byNode.get(obj)
		else if (obj.type === "Identifier") {
			if (byVar.has(obj.name)) site = byVar.get(obj.name)
			else if (imports.has(obj.name))
				calls.push({ name: obj.name, spec: imports.get(obj.name), ...r })
		}
		if (site) mergeArgs(site, r)
	})
	// a resource handed around as a VALUE (`const r = ok ? approve : reject`)
	// is submitted somewhere the scanner cannot follow — its arguments are dynamic
	walk(ast.program, (node, parent) => {
		if (node.type !== "Identifier") return
		if (parent?.type === "MemberExpression" && parent.object === node) return
		if (parent?.type === "VariableDeclarator" && parent.id === node) return
		if (
			parent?.type?.startsWith("Import") ||
			parent?.type?.startsWith("Export")
		)
			return
		if (
			parent?.type === "ObjectProperty" &&
			parent.key === node &&
			!parent.shorthand
		)
			return
		if (byVar.has(node.name)) byVar.get(node.name).dynamic = true
		else if (imports.has(node.name))
			calls.push({
				name: node.name,
				spec: imports.get(node.name),
				keys: new Set(),
				dynamic: true,
			})
	})
	return { sites, calls }
}

function mergeArgs(site, r) {
	if (!site.argsAreKwargs) return
	for (const k of r.keys) site.keys.add(k)
	site.dynamic = site.dynamic || r.dynamic
}

function allSites() {
	const perFile = []
	for (const file of sourceFiles()) {
		let code
		let offset = 0
		if (file.endsWith(".vue")) {
			const { descriptor } = sfc(file)
			code = descriptor.scriptSetup?.content || descriptor.script?.content
			if (!code) continue
			offset = (descriptor.scriptSetup || descriptor.script).loc.start.line - 1
		} else code = read(file)
		perFile.push({ file, ...requestSites(code, rel(file), offset, file) })
	}
	// a resource exported from data/*.js is submitted from the view that imports it
	const exported = new Map() // absPath#name → site
	for (const { sites } of perFile)
		for (const s of sites)
			if (s.exported) exported.set(`${s.absPath}#${s.varName}`, s)
	for (const { file, calls } of perFile) {
		for (const c of calls) {
			const target = resolveImport(c.spec, file)
			const site = target && exported.get(`${target}#${c.name}`)
			if (site) mergeArgs(site, c)
		}
	}
	return perFile.flatMap((p) => p.sites)
}

const normalise = (url) => url?.replace(/^\/api\/method\//, "")

const methods = whitelistedMethods()
const sites = allSites()

test("the backend scan found the hrms API surface", () => {
	assert.ok(methods.size > 50, `only ${methods.size} whitelisted defs found`)
	assert.ok(methods.has("hrms.api.get_doctype_fields"))
	assert.ok(methods.has("hrms.api.remote_checkin.punch"))
})

test("every url the PWA calls resolves to a whitelisted hrms def or an allowlisted core method", () => {
	const unknown = []
	for (const s of sites) {
		if (s.urlDynamic) continue // e.g. url: `${base}/...` — reported below
		if (!s.url) continue // createListResource / createDocumentResource without url: frappe-ui's own client calls
		const url = normalise(s.url)
		if (!methods.has(url) && !(url in CORE))
			unknown.push(`${s.file}:${s.line} → ${url}`)
	}
	assert.deepEqual(unknown, [])
})

test("every url is a string literal the audit can read", () => {
	const dynamic = sites
		.filter((s) => s.urlDynamic)
		.map((s) => `${s.file}:${s.line}`)
	assert.deepEqual(dynamic, [])
})

test("every hrms method receives its required parameters and no unknown kwargs", () => {
	const findings = []
	for (const s of sites) {
		const url = normalise(s.url)
		if (!url) continue
		const sig = methods.get(url) || CORE[url]
		if (!sig) continue
		for (const k of s.keys) {
			if (!sig.varkw && !sig.required.includes(k) && !sig.optional.includes(k))
				findings.push(
					`${s.file}:${s.line} ${url} passes unknown kwarg \`${k}\` (accepts ${
						[...sig.required, ...sig.optional].join(", ") || "nothing"
					})`
				)
		}
		if (s.dynamic) continue // arguments built at call time — cannot be read statically
		for (const r of sig.required) {
			if (!s.keys.has(r))
				findings.push(
					`${s.file}:${s.line} ${url} never passes required \`${r}\` (passes ${
						[...s.keys].join(", ") || "nothing"
					})`
				)
		}
	}
	assert.deepEqual(findings, [], findings.join("\n"))
})

// ---------------------------------------------------------------------------
// Doctype fields read by createListResource
// ---------------------------------------------------------------------------
const STANDARD_FIELDS = new Set([
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"parent",
	"parentfield",
	"parenttype",
	"_user_tags",
	"_comments",
	"_assign",
	"_liked_by",
])

function doctypeJson(doctype) {
	const snake = doctype.toLowerCase().replace(/\s+/g, "_")
	const candidates = [HRMS_PY]
	for (const base of [
		join(REPO, ".."),
		join(process.env.HOME || "", "verify-bench", "apps"),
	]) {
		for (const app of ["erpnext", "frappe"]) {
			const dir = join(base, app, app)
			if (existsSync(dir)) candidates.push(dir)
		}
	}
	for (const root of candidates) {
		for (const module of readdirSync(root)) {
			const path = join(root, module, "doctype", snake, `${snake}.json`)
			if (existsSync(path)) return JSON.parse(readFileSync(path, "utf8"))
		}
	}
	return null
}

// Custom fields hrms installs on core doctypes, declared as
// `"<Doctype>": [ { "fieldname": ... } ]` blocks in these modules.
const CUSTOM_FIELD_SOURCES = [
	"setup.py",
	"utils/extension_custom_fields.py",
	"sync/runner.py",
]

function customFields(doctype) {
	const names = []
	for (const source of CUSTOM_FIELD_SOURCES) {
		const path = join(HRMS_PY, source)
		if (!existsSync(path)) continue
		const text = readFileSync(path, "utf8")
		let start = -1
		while ((start = text.indexOf(`"${doctype}": [`, start + 1)) !== -1) {
			let depth = 0
			let end = start
			for (let i = text.indexOf("[", start); i < text.length; i++) {
				if (text[i] === "[") depth++
				else if (text[i] === "]" && --depth === 0) {
					end = i
					break
				}
			}
			for (const m of text
				.slice(start, end)
				.matchAll(/"fieldname":\s*"(\w+)"/g))
				names.push(m[1])
		}
	}
	return names
}

test("every field a createListResource reads exists on its doctype", () => {
	const findings = []
	const skipped = []
	for (const s of sites) {
		if (s.kind !== "createListResource" || !s.doctype || !s.fields.length)
			continue
		const json = doctypeJson(s.doctype)
		if (!json) {
			skipped.push(
				`${s.file}:${s.line} ${s.doctype} (doctype JSON not on disk)`
			)
			continue
		}
		const known = new Set([
			...STANDARD_FIELDS,
			...json.fields.map((f) => f.fieldname),
			...customFields(s.doctype),
		])
		if (json.istable) known.add("parent")
		for (const f of s.fields) {
			if (f === null || f === "*" || f.includes("`") || f.includes(" as "))
				continue
			if (!known.has(f))
				findings.push(
					`${s.file}:${s.line} ${s.doctype}.${f} is not a field of the doctype`
				)
		}
	}
	if (skipped.length)
		console.log(
			"[api-contract] doctype JSON not found (skipped):\n  " +
				skipped.join("\n  ")
		)
	assert.deepEqual(findings, [], findings.join("\n"))
})

test("the site scanner reads params, makeParams and submit() arguments", () => {
	const code = `
const own = () => ({ employee: e, limit: 10 })
const a = createResource({ url: "hrms.api.get_ot_requests", makeParams: own })
const b = createResource({ url: "hrms.api.get_leave_types", params: { employee: x } })
b.fetch({ date: today })
const c = createListResource({ doctype: "Employee Issue", fields: ["name", "nope"] })
`
	const { sites } = requestSites(code, "t.js")
	assert.deepEqual([...sites[0].keys], ["employee", "limit"])
	assert.deepEqual([...sites[1].keys], ["employee", "date"])
	assert.deepEqual(sites[2].fields, ["name", "nope"])
})

// Guard against the audit going hollow: if a scanner change marked everything
// dynamic, the required-parameter check above would pass by never looking.
test("most request sites are readable statically", () => {
	const withUrl = sites.filter((s) => s.url)
	const static_ = withUrl.filter((s) => !s.dynamic)
	console.log(
		`[api-contract] ${withUrl.length} request sites, ${
			static_.length
		} with static arguments, ${withUrl.length - static_.length} dynamic`
	)
	assert.ok(
		static_.length >= 60,
		`only ${static_.length} of ${withUrl.length} sites are statically readable`
	)
})

test("the scanner sees a missing required parameter and an unknown kwarg", () => {
	const code = `
const a = createResource({ url: "hrms.api.get_leave_types", params: { employee: x } })
const b = createResource({ url: "hrms.api.get_shifts", params: { employe: x } })
`
	const { sites } = requestSites(code, "t.js")
	const sig = methods.get("hrms.api.get_leave_types")
	assert.ok(
		sig.required.includes("date") && !sites[0].keys.has("date"),
		"date is required and not passed"
	)
	assert.ok(
		!methods.get("hrms.api.get_shifts").optional.includes("employe"),
		"the misspelt kwarg is unknown"
	)
})
