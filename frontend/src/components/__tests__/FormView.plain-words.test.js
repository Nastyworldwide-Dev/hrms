// The form shell names the THING, not the doctype (2.0 slice 1.1).
//
// `FormView` is the generic shell behind every request screen, and it builds
// its own user-facing copy out of `props.doctype`. So an employee deleting a
// punch reads "Delete Employee Checkin", and one filing time off reads
// "Permanently submit Attendance Request". Those are table names. Nobody
// outside this repo has ever heard them, and they appear in the two moments
// that most need to be understood: a confirm dialog and a failure toast.
//
// `__(props.doctype)` does not save it. The translation files carry UI strings,
// not doctype names, so the lookup misses and the raw name falls through — and
// on an English install there is nothing to translate to anyway. The fix is
// not a better translation, it is not passing a table name to a person.
//
// THE RULE: every screen that mounts FormView gives it a `noun` — the word an
// employee would use — and the shell's copy is built from that. A screen that
// forgets gets a generic sentence ("this request"), never the doctype.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.vue$/.test(entry) && !path.includes("__tests__")) out.push(path)
	}
	return out
}

/** Comments blanked — a comment explaining the rule names what it forbids. */
function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

test("no sentence an employee reads is built from the doctype", () => {
	const source = code(read("components/FormView.vue"))
	// Every `__("... {0} ...", [something])` whose argument is the doctype.
	const offenders = []
	for (const m of source.matchAll(/__\(\s*(["'`])((?:(?!\1).)*)\1\s*,\s*\[([^\]]*)\]/g)) {
		if (/props\.doctype/.test(m[3])) offenders.push(m[2])
	}
	assert.deepEqual(offenders, [], "these sentences put a table name in front of an employee")
})

test("the shell asks for a word, and it is required", () => {
	const source = read("components/FormView.vue")
	assert.match(source, /noun:\s*\{/, "FormView takes a `noun` prop")
	assert.match(
		source,
		/noun:\s*\{[^}]*default:/,
		"with a default, because a screen that forgets must degrade to a sentence, not to a crash"
	)
	// The default is the generic sentence, never the doctype.
	const prop = source.slice(
		source.indexOf("noun: {"),
		source.indexOf("}", source.indexOf("noun: {"))
	)
	assert.doesNotMatch(prop, /doctype/, "the fallback is a plain word, not the table name")
})

test("every screen that mounts the shell passes its own word", () => {
	const missing = []
	for (const path of walk(join(SRC, "views"))) {
		const text = code(readFileSync(path, "utf8"))
		const tag = text.match(/<FormView[\s\S]*?>/)
		if (!tag) continue
		// A screen that renders the shell without a noun gets the generic
		// fallback — correct, but it means nobody chose the word. Every screen
		// in views/ is a screen somebody can name.
		if (!/:?noun=/.test(tag[0])) missing.push(path.slice(SRC.length))
	}
	assert.deepEqual(missing, [], "name the thing this screen is about")
})

test("the word is a word, not a doctype in disguise", () => {
	// `:noun="doctype"` would satisfy every check above and change nothing.
	const offenders = []
	for (const path of walk(join(SRC, "views"))) {
		const text = code(readFileSync(path, "utf8"))
		for (const m of text.matchAll(/:noun="([^"]*)"/g)) {
			if (/doctype/i.test(m[1])) offenders.push(`${path.slice(SRC.length)}: ${m[1]}`)
		}
	}
	assert.deepEqual(offenders, [], "pass the employee's word, not the table's")
})
