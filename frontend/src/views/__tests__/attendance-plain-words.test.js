// Attendance screens name the thing, not the table (2.0 slice 2.1).
//
// Three of them are titled with a doctype: "Employee Checkin History", "Shift
// Assignment History", "Attendance Request History". An employee looking for
// the times they tapped in does not know what an Employee Checkin is, and
// "Shift Assignment" is the table that stores a roster line — the word for it
// is "shifts".
//
// And the attendance dashboard carries the exact defect slice 2.2 just fixed
// on the OT row: `__(claimableOt.data.compensation)` translates the server's
// own Select value, so "Overtime Pay" reaches the screen because the
// translation files do not contain it. The same two wire values, the same
// need for an explicit mapping, one screen over.
//
// This slice is wording. The layout work the plan describes for these screens
// — the day sheet, the missing-punch flag, travel and training dots — needs
// backend that does not exist yet (§3.2 marks them N), and building it is a
// feature rather than a rename.
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

//: Doctype names that must never appear in something an employee reads. Each
//: is a real table in this app.
const TABLE_NAMES = [
	"Employee Checkin",
	"Shift Assignment",
	"Attendance Request",
	"Shift Request",
	"Leave Application",
	"Expense Claim",
]

test("no attendance screen is titled with a doctype", () => {
	const offenders = []
	for (const path of walk(join(SRC, "views/attendance"))) {
		const text = code(readFileSync(path, "utf8"))
		const title = text.match(/pageTitle="__\(['"]([^'"]*)['"]\)"/)
		if (!title) continue
		for (const table of TABLE_NAMES) {
			if (title[1].includes(table)) offenders.push(`${path.slice(SRC.length)}: ${title[1]}`)
		}
	}
	assert.deepEqual(offenders, [], "a title is the first thing read; it must not be a table name")
})

test("the punch history is named for what an employee taps", () => {
	const list = code(read("views/attendance/EmployeeCheckinList.vue"))
	const title = list.match(/pageTitle="__\('([^']*)'\)"/)
	assert.ok(title, "it has a title")
	assert.match(title[1], /check|clock|punch/i, "and it still says what it holds")
})

test("no attendance screen translates a raw server value", () => {
	// The same defect as the OT row and the shift chip: `__(x)` where x came
	// from the server means the translation files decide whether an employee
	// sees a word or a table's vocabulary — and they do not contain doctype
	// Select values, so the raw value falls through.
	const offenders = []
	for (const path of [...walk(join(SRC, "views/attendance")), join(SRC, "components")].flatMap(
		(p) => (statSync(p).isDirectory() ? walk(p) : [p])
	)) {
		const text = code(readFileSync(path, "utf8"))
		for (const m of text.matchAll(
			/__\(\s*([\w.]*(?:compensation|workflow_state|docstatus))\s*[,)]/g
		)) {
			offenders.push(`${path.slice(SRC.length)}: __(${m[1]})`)
		}
	}
	assert.deepEqual(offenders, [], "map the wire value explicitly; do not translate it")
})

test("the claim prompt says which of the two it is", () => {
	// "Overtime Pay" or "Replacement Leave" — the same two values the OT row
	// maps. The dashboard's prompt is the moment an employee decides whether
	// to tap, so it has to say what tapping gets them.
	const dash = code(read("views/attendance/Dashboard.vue"))
	assert.match(dash, /Overtime Pay/, "the wire value is named, so the mapping is legible")
	assert.match(dash, /Overtime pay|day off/i, "and the employee's words are what render")
})

test("the shifts list is named for shifts", () => {
	const list = code(read("views/attendance/ShiftAssignmentList.vue"))
	const title = list.match(/pageTitle="__\('([^']*)'\)"/)
	assert.ok(title, "it has a title")
	assert.match(title[1], /shift/i, "it is about shifts")
	assert.doesNotMatch(title[1], /Assignment/, '"Shift Assignment" is the table that stores one')
})
