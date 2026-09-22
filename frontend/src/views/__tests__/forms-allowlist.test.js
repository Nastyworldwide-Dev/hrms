// A form shows the fields it asked for, not the fields nobody hid (2.0 slice 3.1).
//
// Both request forms filter a doctype's fields with a BLACKLIST: a hand-written
// `excludeFields` naming `naming_series`, `letter_head`, `salary_slip` and the
// rest. That is backwards. A blacklist decides what to hide, so anything it has
// not heard of is SHOWN — and the list is a snapshot of the schema on the day
// somebody wrote it, while the schema is a live thing that ERPNext, HRMS and
// this app all add to.
//
// It is not theoretical. Read against the running site's own metadata, the
// leave form's blacklist lets through:
//
//   synced_from_instance   this app's cross-instance mirror flag
//   color                  a Desk calendar colour
//   amended_from           Frappe's link to the cancelled document it replaced
//
// None of those is a question to ask an employee filing time off, and none was
// deliberately allowed — they simply were not on a list written before they
// existed. The expense form's blacklist has grown to eighteen entries chasing
// the same problem.
//
// THE RULE: each form names the fields it wants. A field that is not named does
// not render, so the next migration cannot leak anything, and adding a field to
// the screen becomes a deliberate act.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const FORMS = ["views/leave/Form.vue", "views/expense_claim/Form.vue"]

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

test("no form decides what to show by listing what to hide", () => {
	const offenders = []
	for (const form of FORMS) {
		if (/excludeFields/.test(code(read(form)))) offenders.push(form)
	}
	assert.deepEqual(offenders, [], "a blacklist shows everything it has not heard of")
})

test("each form names the fields it wants", () => {
	for (const form of FORMS) {
		const source = code(read(form))
		assert.match(source, /FIELDS\s*=\s*\[/, `${form}: an explicit list of fieldnames`)
		// And the filter must USE it — a constant nothing reads is a comment.
		assert.match(
			source,
			/FIELDS[^\n]*\.includes\(|includes\([^)]*fieldname/,
			`${form}: the filter keeps only what the list names`
		)
	}
})

test("the fields that leaked today are not in any list", () => {
	// Read from the running site's metadata, not guessed: these three reach the
	// leave form right now because nobody blacklisted them.
	for (const form of FORMS) {
		const source = code(read(form))
		for (const leaked of ["synced_from_instance", "amended_from", '"color"']) {
			assert.doesNotMatch(
				source,
				new RegExp(`FIELDS[\\s\\S]*?${leaked.replace(/"/g, '"')}[\\s\\S]*?\\]`),
				`${form} must not ask for ${leaked}`
			)
		}
	}
})

test("a layout field is kept by its kind, not by its name", () => {
	// Section and column breaks are named `section_break_5`, `column_break_18`,
	// `column_break_imlz` — generated names that change when somebody reorders
	// the doctype in Desk. Naming them in an allowlist would be a list that
	// breaks on a layout edit, so they pass on FIELDTYPE.
	for (const form of FORMS) {
		const source = code(read(form))
		assert.match(
			source,
			/Section Break|Column Break/,
			`${form}: layout fields pass by type, or the list breaks whenever Desk renumbers them`
		)
	}
})

test("what the employee could fill in before, they still can", () => {
	// The point is to remove plumbing, not to shrink the form. These are the
	// fields the blacklists deliberately LET THROUGH — every one must be named.
	// Scoped to the LIST. These names also appear in watchers and lookups —
	// `half_day_date` is in four places in the leave form — so a whole-file
	// match passed even with the field removed from the allowlist, and the
	// mutant survived.
	const listOf = (form) => {
		const text = code(read(form))
		const at = text.indexOf("const FIELDS = [")
		return text.slice(at, text.indexOf("]", at))
	}
	const leave = listOf("views/leave/Form.vue")
	for (const field of [
		"leave_type",
		"from_date",
		"to_date",
		"half_day",
		"half_day_date",
		"description",
		"leave_approver",
	]) {
		assert.match(leave, new RegExp(`"${field}"`), `leave form still offers ${field}`)
	}
	const claim = listOf("views/expense_claim/Form.vue")
	for (const field of ["expenses", "posting_date", "expense_approver"]) {
		assert.match(claim, new RegExp(`"${field}"`), `expense form still offers ${field}`)
	}
})
