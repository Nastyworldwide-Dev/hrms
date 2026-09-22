// Script-setup ordering (static audit, 15 Sep 2026): the KPI / OT crash class.
//
// `watch(() => teamData.value, …)` runs its getter the moment the watch is
// created; `const teamData = computed(…)` sat twenty lines further down, still
// in the temporal dead zone, and the KPI page threw during setup — Ionic then
// kept a view with no element and every later navigation errored, so the
// screen looked frozen (d8c5f58b4). OTRequestForm.vue had the identical shape.
//
// The rule is general: in a `<script setup>` block (or a plain module) every
// expression that is evaluated EAGERLY while the block runs — a top-level
// statement, the source / getter of watch(), the body of watchEffect(), the
// getter of computed(), the callback of an `immediate: true` watch — must not
// reference a `const`/`let`/`class` declared later in the same block.
// Function bodies that only run later (handlers, onMounted callbacks, watch
// callbacks without `immediate`) are exempt: by the time they run, every
// binding exists.
//
// computed() getters are lazy at runtime, but they are included on purpose: a
// getter that reads a later binding is one `watch(thatComputed)` away from the
// crash, and ordering declarations before their readers costs nothing.
import { test } from "node:test"
import assert from "node:assert/strict"
import { babelParse } from "@vue/compiler-sfc"
import { sourceFiles, sfc, read, rel, lineOf } from "./_lib.mjs"

const EAGER_ALL_ARGS = new Set([
	"watchEffect",
	"watchPostEffect",
	"watchSyncEffect",
	"computed",
])
const FUNCTION_TYPES = new Set([
	"ArrowFunctionExpression",
	"FunctionExpression",
	"FunctionDeclaration",
	"ObjectMethod",
	"ClassMethod",
	"ClassPrivateMethod",
])

// Every top-level binding that has a temporal dead zone, with where it starts.
function tdzBindings(program) {
	const out = new Map()
	// keyed by the STATEMENT start so a self-reference inside a binding's own
	// initializer (`session = reactive({ isLoggedIn: computed(() => session.user) })`)
	// compares equal, not later
	const collect = (decl, start) => {
		if (decl.type === "VariableDeclaration" && decl.kind !== "var") {
			for (const d of decl.declarations)
				for (const name of patternNames(d.id)) out.set(name, start)
		} else if (decl.type === "ClassDeclaration" && decl.id)
			out.set(decl.id.name, start)
	}
	for (const stmt of program.body) {
		collect(stmt, stmt.start)
		if (stmt.type === "ExportNamedDeclaration" && stmt.declaration)
			collect(stmt.declaration, stmt.start)
	}
	return out
}

function patternNames(node, out = []) {
	if (!node) return out
	switch (node.type) {
		case "Identifier":
			out.push(node.name)
			break
		case "ObjectPattern":
			for (const p of node.properties)
				patternNames(p.type === "RestElement" ? p.argument : p.value, out)
			break
		case "ArrayPattern":
			for (const e of node.elements) patternNames(e, out)
			break
		case "RestElement":
			patternNames(node.argument, out)
			break
		case "AssignmentPattern":
			patternNames(node.left, out)
			break
	}
	return out
}

// Is this function node evaluated at creation time by the call it is passed to?
function isEagerCallback(fn, parent, argIndex) {
	if (!parent || parent.type !== "CallExpression" || argIndex < 0) return false
	const callee = parent.callee
	const name = callee.type === "Identifier" ? callee.name : null
	if (!name) return false
	if (EAGER_ALL_ARGS.has(name)) return true
	if (name === "watch") {
		if (argIndex === 0) return true
		if (argIndex === 1) {
			const opts = parent.arguments[2]
			return Boolean(
				opts?.type === "ObjectExpression" &&
					opts.properties.some(
						(p) =>
							p.type === "ObjectProperty" &&
							((p.key.type === "Identifier" && p.key.name === "immediate") ||
								p.key.value === "immediate") &&
							p.value.type === "BooleanLiteral" &&
							p.value.value === true
					)
			)
		}
	}
	return false
}

// A `computed({ get() {} })` getter is eager for the same reason.
function isComputedGetter(node, parent, grand) {
	return (
		(node.type === "ObjectMethod" ||
			(parent?.type === "ObjectProperty" && parent.value === node)) &&
		grand?.type === "CallExpression" &&
		grand.callee.type === "Identifier" &&
		grand.callee.name === "computed"
	)
}

// Walks one top-level statement, reporting eager references to later bindings.
function eagerReferences(stmt, bindings, report) {
	const visit = (node, parent, grand, locals, argIndex) => {
		if (!node || typeof node.type !== "string") return
		if (FUNCTION_TYPES.has(node.type)) {
			const eager =
				isEagerCallback(node, parent, argIndex) ||
				isComputedGetter(node, parent, grand) ||
				// an IIFE runs now
				(parent?.type === "CallExpression" && parent.callee === node)
			if (!eager) return
			const inner = new Set(locals)
			for (const p of node.params) for (const n of patternNames(p)) inner.add(n)
			if (node.id) inner.add(node.id.name)
			collectLocals(node.body, inner)
			visitChildren(node, parent, inner)
			return
		}
		if (node.type === "Identifier") {
			// not a reference: property keys, member property names, labels
			if (
				parent?.type === "MemberExpression" &&
				parent.property === node &&
				!parent.computed
			)
				return
			if (
				parent?.type === "OptionalMemberExpression" &&
				parent.property === node &&
				!parent.computed
			)
				return
			if (
				parent?.type === "ObjectProperty" &&
				parent.key === node &&
				!parent.computed &&
				!parent.shorthand
			)
				return
			if (parent?.type === "ObjectMethod" && parent.key === node) return
			if (parent?.type === "VariableDeclarator" && parent.id === node) return
			if (
				(parent?.type === "ClassDeclaration" ||
					parent?.type === "FunctionDeclaration") &&
				parent.id === node
			)
				return
			if (
				parent?.type === "ImportSpecifier" ||
				parent?.type === "ImportDefaultSpecifier"
			)
				return
			if (
				parent?.type === "LabeledStatement" ||
				parent?.type === "BreakStatement" ||
				parent?.type === "ContinueStatement"
			)
				return
			if (locals.has(node.name)) return
			const declaredAt = bindings.get(node.name)
			if (declaredAt !== undefined && declaredAt > stmt.start) report(node)
			return
		}
		visitChildren(node, parent, locals)
	}
	const visitChildren = (node, parent, locals) => {
		for (const key of Object.keys(node)) {
			if (
				key === "loc" ||
				key === "start" ||
				key === "end" ||
				key === "leadingComments" ||
				key === "trailingComments"
			)
				continue
			const child = node[key]
			if (Array.isArray(child)) {
				child.forEach(
					(c, i) =>
						c &&
						typeof c.type === "string" &&
						visit(c, node, parent, locals, key === "arguments" ? i : -1)
				)
			} else if (child && typeof child.type === "string")
				visit(child, node, parent, locals, -1)
		}
	}
	visit(stmt, null, null, new Set(), -1)
}

// Names declared anywhere inside a function body shadow the module bindings.
function collectLocals(node, into) {
	if (!node || typeof node !== "object") return
	if (Array.isArray(node)) return node.forEach((n) => collectLocals(n, into))
	if (node.type === "VariableDeclarator")
		for (const n of patternNames(node.id)) into.add(n)
	if (node.type === "FunctionDeclaration" && node.id) into.add(node.id.name)
	if (node.type === "CatchClause" && node.param)
		for (const n of patternNames(node.param)) into.add(n)
	for (const key of Object.keys(node)) {
		if (key === "loc") continue
		const child = node[key]
		if (child && typeof child === "object") collectLocals(child, into)
	}
}

export function scanModule(code, file, lineOffset = 0) {
	const ast = babelParse(code, { sourceType: "module", plugins: ["jsx"] })
	const bindings = tdzBindings(ast.program)
	const findings = []
	for (const stmt of ast.program.body) {
		eagerReferences(stmt, bindings, (id) => {
			findings.push(
				`${file}:${lineOffset + lineOf(code, id.start)} reads \`${
					id.name
				}\` before its declaration at line ${
					lineOffset + lineOf(code, bindings.get(id.name))
				}`
			)
		})
	}
	return findings
}

test("no <script setup> or module evaluates a binding before it is declared", () => {
	const findings = []
	for (const file of sourceFiles()) {
		let code
		let offset = 0
		if (file.endsWith(".vue")) {
			const { descriptor } = sfc(file)
			code = descriptor.scriptSetup?.content
			if (!code) continue
			offset = descriptor.scriptSetup.loc.start.line - 1
		} else code = read(file)
		findings.push(...scanModule(code, rel(file), offset))
	}
	assert.deepEqual(
		findings,
		[],
		`temporal-dead-zone reads:\n${findings.join("\n")}`
	)
})

// The scanner must actually see the KPI shape, or the test above is a tautology.
test("the scanner catches the KPI Dashboard shape", () => {
	const code = `
import { watch, computed, ref } from "vue"
const teamResource = ref(null)
watch(() => teamData.value, () => {})
const teamData = computed(() => teamResource.value)
`
	assert.equal(scanModule(code, "kpi.vue").length, 1)
})

test("the scanner accepts deferred readers and shadowed names", () => {
	const code = `
import { watch, computed, ref, onMounted } from "vue"
const a = ref(1)
watch(a, () => later.value)          // callback runs later
onMounted(() => later.value)          // runs later
function handler(later) { return later }  // shadowed param
const b = computed(() => a.value)
const later = ref(2)
watch(() => later.value, () => {}, { immediate: true })
`
	assert.deepEqual(scanModule(code, "ok.vue"), [])
})

test("the scanner flags an immediate watch callback", () => {
	const code = `
import { watch, ref } from "vue"
const a = ref(1)
watch(a, () => later.value, { immediate: true })
const later = ref(2)
`
	assert.equal(scanModule(code, "imm.vue").length, 1)
})
