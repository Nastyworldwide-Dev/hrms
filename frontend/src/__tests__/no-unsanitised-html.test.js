// Nothing renders server HTML into the page without sanitising it first
// (pre-2.0 R1, checklist §8 "avoid unsafe innerHTML / protect against XSS").
//
// Three templates hand a server string to `v-html`, which is an unguarded
// write into the DOM: any <script>, any onerror=, any javascript: href in that
// string runs as the logged-in employee. None of the three is exploitable
// today — Frappe sanitises Helpdesk's rich text, SOP content is authored by
// HR, notification messages are built server-side — but every one of those is
// a statement about the CURRENT backend, and none of them is enforced here.
// The checklist's own reason: "users can inspect and manipulate everything
// running in their browser", and a field that becomes user-writable later
// changes an internal tool into a stored-XSS vector with no code change on
// this side at all.
//
// `loudRequest.firstMessage` is the pattern that was already right: it strips
// every tag before the toast renders it, so a server refusal carrying a Desk
// link reaches the employee as words. The rule below generalises that — each
// v-html site must pass its value through a named sanitiser, so the guarantee
// is in the code rather than in a comment about who writes the field.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("..", import.meta.url))

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.(vue|js)$/.test(entry) && !path.includes("__tests__")) out.push(path)
	}
	return out
}

const FILES = walk(SRC)
const source = (path) => readFileSync(path, "utf8")

// Strip comments first: a comment explaining why a site is sanitised names
// `v-html`, and counting it would make documentation a violation — the same
// defect the usage gate and the dvh rule both had.
function code(path) {
	return source(path)
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

test("every v-html renders a sanitised value", () => {
	const offenders = []
	for (const path of FILES) {
		for (const m of code(path).matchAll(/v-html="([^"]*)"/g)) {
			// `safeHtml(...)` is the one door. A bare field, a ternary over two
			// bare fields, or a template string all reach the DOM unchecked.
			if (!m[1].trim().startsWith('safeHtml(')) offenders.push(`${path.slice(SRC.length)}: ${m[1]}`)
		}
	}
	assert.deepEqual(offenders, [], "pass it through safeHtml() from @/utils/safeHtml")
})

test("nothing writes innerHTML by hand", () => {
	const offenders = []
	for (const path of FILES) {
		// safeHtml IS the sanitiser: it writes into a detached <template>,
		// which parses without executing, and that is the whole technique.
		// Exempting it by name keeps the rule absolute everywhere else.
		if (path.endsWith('utils/safeHtml.js')) continue
		if (/\binnerHTML\s*=/.test(code(path))) offenders.push(path.slice(SRC.length))
	}
	assert.deepEqual(offenders, [], "innerHTML bypasses both Vue and the sanitiser")
})

// The sanitiser itself, exercised — a test that only checked call sites would
// pass against a safeHtml() that returned its input unchanged.
test("the sanitiser removes what it promises to remove", async () => {
	const { safeHtml } = await import("../utils/safeHtml.js")
	const cases = [
		["<script>alert(1)</script>hello", "script tag"],
		['<img src=x onerror="alert(1)">', "inline event handler"],
		['<a href="javascript:alert(1)">tap</a>', "javascript: url"],
		['<div style="background:url(javascript:alert(1))">x</div>', "javascript: in a style"],
		["<iframe src=//evil></iframe>", "embedded frame"],
		["<object data=x></object>", "embedded object"],
		["<svg><script>alert(1)</script></svg>", "script inside svg"],
		["<form action=/steal><input name=pw></form>", "a form that posts elsewhere"],
	]
	// Holds on BOTH paths. Under this runner there is no DOM, so what is being
	// exercised is the text branch — which is why the assertion is "none of
	// this survives" rather than "the markup came back tidy".
	for (const [input, what] of cases) {
		const out = safeHtml(input)
		assert.doesNotMatch(
			out,
			/<script|onerror|javascript:|<iframe|<object|<form/i,
			`kept the ${what}`
		)
	}
})

test("the sanitiser keeps the formatting these screens rely on", async () => {
	// SOP bodies and Helpdesk replies are rich text. A sanitiser that stripped
	// everything would be safe and useless — HR's procedure would arrive as one
	// run-on paragraph, which is how `firstMessage` behaves ON PURPOSE for a
	// one-line toast and exactly wrong for a document.
	//
	// Asserted against the ALLOW-LIST rather than by round-tripping markup:
	// this runner has no DOM (no jsdom in the repo, and every other test here
	// is source-asserted), so `safeHtml` takes its no-DOM branch and returns
	// text. What can be checked without a browser is the vocabulary the DOM
	// path will keep — and that it is a list of NAMES, not a list of attacks.
	const source = readFileSync(join(SRC, "utils/safeHtml.js"), "utf8")
	const tags = source.slice(source.indexOf("ALLOWED_TAGS"), source.indexOf("ALLOWED_ATTRS"))
	for (const tag of ["h2", "p", "strong", "em", "ul", "li", "a", "table", "td", "blockquote"]) {
		assert.match(tags, new RegExp(`"${tag}"`), `<${tag}> is legitimate document markup`)
	}
	for (const tag of ["script", "iframe", "object", "embed", "form", "style"]) {
		assert.doesNotMatch(tags, new RegExp(`"${tag}"`), `<${tag}> must not be allowed`)
	}
	const attrs = source.slice(source.indexOf("ALLOWED_ATTRS"), source.indexOf("function safeUrl"))
	assert.match(attrs, /"href"/, "an ordinary link survives")
	assert.doesNotMatch(attrs, /"style"/, "inline style can load a url()")
	assert.doesNotMatch(attrs, /"srcset"|"formaction"/, "these carry urls too")
})

// The no-DOM path is not a fallback nobody takes: it is what runs under SSR
// and in every unit test that imports one of these components. It must be at
// least as strict as the DOM path, never more permissive.
test("with no DOM the sanitiser returns text, not markup it has not checked", async () => {
	const { safeHtml } = await import("../utils/safeHtml.js")
	assert.equal(safeHtml("<script>alert(1)</script>hello"), "hello")
	assert.equal(safeHtml("<p>a</p><p>b</p>"), "ab")
	assert.equal(safeHtml('<img src=x onerror="alert(1)">'), "")
	assert.equal(safeHtml(null), "")
})
