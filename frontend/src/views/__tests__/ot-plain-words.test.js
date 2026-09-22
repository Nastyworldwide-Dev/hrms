// Overtime reads as what is owed, not as a document (2.0 slice 2.2).
//
// An OT claim is the one request in this app that is ABOUT MONEY, and the
// screens describe it as paperwork. The history is titled "OT Request
// History"; its filter offers "Compensation" with the options "Overtime Pay"
// and "Replacement Leave"; a row reads "1.5h overtime · Overtime Pay".
//
// Every one of those is the doctype's own vocabulary. "OT Request" is a table.
// "Compensation" is the field's label in Desk. And the row leads with HOURS,
// which is the input — the employee already knows how long they stayed. What
// they came to find out is whether it turned into money or into a day off,
// and whether anybody has agreed to it yet.
//
// The fix is wording and ordering, not new data: `compensation` already says
// which of the two it is, and the status chip already says whether it is
// settled. This is the same class as slice 1.1 (a doctype name in a dialog)
// and 1.2 (a docstatus word in a chip), in the one place where the word
// happens to be about pay.
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

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

//: Every screen and component that renders overtime.
const OT_FILES = [
	...walk(join(SRC, "views/ot")),
	join(SRC, "components/OTRequestItem.vue"),
	join(SRC, "components/ReplacementLeaveClaimItem.vue"),
]

test("no overtime screen shows a doctype's name to an employee", () => {
	const offenders = []
	for (const path of OT_FILES) {
		const text = code(readFileSync(path, "utf8"))
		// Inside a translated string only: `doctype="OT Request"` is a prop and
		// correct — it names the table TO THE SERVER, which is what it is for.
		for (const m of text.matchAll(/__\(\s*(["'])((?:(?!\1).)*)\1/g)) {
			if (/OT Request|Replacement Leave Claim/.test(m[2])) {
				offenders.push(`${path.slice(SRC.length)}: ${m[2]}`)
			}
		}
	}
	assert.deepEqual(offenders, [], "an employee never reads a table name")
})

test("the history is named for what it holds", () => {
	const list = code(read("views/ot/OTRequestList.vue"))
	const title = list.match(/pageTitle="__\('([^']*)'\)"/)
	assert.ok(title, "the list has a title")
	assert.doesNotMatch(title[1], /OT Request/, "that is the doctype")
	assert.match(title[1], /overtime|Overtime/, "and it is still about overtime")
})

test("the filter asks what the employee wants to know", () => {
	// "Compensation" is the field's label in Desk. The question underneath it
	// is "paid, or a day off?" — which is what the two options already say.
	const list = code(read("views/ot/OTRequestList.vue"))
	assert.doesNotMatch(list, /label: __\("Compensation"\)/, "Desk's word for the field")
	assert.doesNotMatch(
		list,
		/label: __\("OT Date"\)/,
		'"OT Date" is a fieldname with a space in it'
	)
})

test("a row leads with the outcome, not the input", () => {
	// "1.5h overtime" is the INPUT — the employee knows how long they stayed.
	// What the row is for is the outcome: whether it became pay or a day off,
	// and whether anyone has agreed yet.
	const item = code(read("components/OTRequestItem.vue"))
	const left = item.slice(item.indexOf("#left"), item.indexOf("#right"))
	// The first line may be a computed rather than an inline `__()` — which is
	// the better place once the word is DERIVED from the compensation rather
	// than formatted from the hours. Follow the binding into the script.
	const first = left.match(/\{\{\s*([\w.]+)\s*\}\}|\{\{\s*__\(([^}]*)\}\}/)
	assert.ok(first, "the row has a first line")
	const source = first[1]
		? item.slice(item.indexOf(`const ${first[1]} = computed`), item.indexOf("const status"))
		: first[2]
	assert.match(source, /compensation|paid|leave|owed/i, "the first line says what it turned into")
	// ...and the hours moved to the detail line, where the date already is.
	const detail = left.slice(left.indexOf("text-xs"))
	assert.match(detail, /claimed_hours/, "the hours are the detail now, not the headline")
})

test("the two outcomes are named in the employee's words", () => {
	// `compensation` is "Overtime Pay" or "Replacement Leave" on the wire —
	// the doctype's Select options, which cannot change without a migration.
	// The SCREEN may still say it better, and the mapping has to be explicit
	// rather than a translation of the raw value.
	const item = code(read("components/OTRequestItem.vue"))
	assert.match(item, /Overtime Pay/, "the wire value is named, so the mapping is legible")
	assert.doesNotMatch(
		item,
		/__\(props\.doc\.compensation\)/,
		"translating the raw value is how the server's word reaches the screen"
	)
})
