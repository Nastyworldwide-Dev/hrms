// A status chip says what happened, in words (2.0 slice 1.2).
//
// Two defects, different shapes, one symptom.
//
// UNTRANSLATED. `ShiftAssignmentItem` renders `:label="status"` with no
// `__()` at all, so whatever string it computed reaches the screen raw. Every
// other item component in the app translates its label; this one was missed.
//
// AND THE WORD IS WRONG ANYWAY. Its status is not a workflow state — it is
// invented from `docstatus`: `props.doc.docstatus ? "Submitted" : "Draft"`.
// Those are Frappe's own two words for "this row is saved" and "this row is
// not", and neither means anything to a person looking at their own shift.
// "Draft" in particular reads as "you have not finished it", when the shift is
// real and simply has not been submitted by whoever rosters it.
//
// So translating it is not the fix. A translation of the wrong word is the
// wrong word in another language. The chip has to say the thing that happened.
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

test("every chip label goes through the translator", () => {
	const offenders = []
	for (const path of walk(SRC)) {
		const text = code(readFileSync(path, "utf8"))
		for (const m of text.matchAll(/<GStatusChip[\s\S]*?\/>/g)) {
			const label = m[0].match(/:label="([^"]*)"/)
			if (!label) continue
			const bound = label[1].trim()
			if (/__\(/.test(bound)) continue
			// A label function passed in as a prop is translated by its caller
			// (HelpSplitList's chipLabel: HelpdeskList/IssueList pass __()).
			if (/^chipLabel\(/.test(bound)) continue
			// A binding may name a computed that translates INSIDE the script —
			// which is the better place for it once the word is derived rather
			// than passed through. Follow the name; only an identifier that
			// reaches the template untranslated is a violation.
			const computedSource = text.match(
				new RegExp(`const ${bound}\\s*=\\s*computed\\([\\s\\S]*?\\n\\}\\)`)
			)
			if (computedSource && /__\(/.test(computedSource[0])) continue
			offenders.push(`${path.slice(SRC.length)}: ${bound}`)
		}
	}
	assert.deepEqual(offenders, [], "a raw binding puts the server's word on the screen")
})

// Frappe's `docstatus` is 0/1/2 — an internal flag for "not submitted",
// "submitted", "cancelled". Rendering its name is rendering a database column.
test("no chip is labelled from docstatus", () => {
	const offenders = []
	for (const path of walk(SRC)) {
		const text = code(readFileSync(path, "utf8"))
		if (!/<GStatusChip/.test(text)) continue
		// Only where the word would be READ. `status` still carries Frappe's
		// vocabulary because GStatusChip colours from it and already knows
		// those names — what must not happen is that string reaching a label.
		const labels = [...text.matchAll(/const label\s*=\s*computed\([\s\S]*?\n\}\)/g)]
			.map((m) => m[0])
			.join("\n")
		if (/["'](Draft|Submitted)["']/.test(labels)) offenders.push(path.slice(SRC.length))
	}
	assert.deepEqual(
		offenders,
		[],
		'"Draft" and "Submitted" are Frappe\'s words for a saved row, not a person\'s'
	)
})

test("the shift chip says what happened to the shift", () => {
	const source = read("components/ShiftAssignmentItem.vue")
	// A real workflow state still wins when one exists — this is only about
	// the fallback that was inventing words from docstatus.
	assert.match(source, /workflowStateField/, "a real workflow state is still preferred")
	assert.match(
		source,
		/__\(\s*"Scheduled"/,
		"a submitted shift is one the employee is rostered for"
	)
	assert.match(source, /__\(\s*"Not scheduled yet"/, "and an unsubmitted one is not yet theirs")
})

// The chip's COLOUR is chosen from `status`, and the label is what is read.
// They must not drift: a chip that reads "Scheduled" and colours itself as a
// draft is worse than either, because the two halves disagree in the same
// glance.
test("the word and the colour come from the same fact", () => {
	const source = read("components/ShiftAssignmentItem.vue")
	const chip = source.match(/<GStatusChip[\s\S]*?\/>/g).join("\n")
	assert.match(chip, /:status="status"/, "the colour still reads the status")
	assert.match(chip, /:label="[^"]*label[^"]*"/i, "and the label is derived beside it")
})
