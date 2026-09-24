// A section heading with nothing under it is noise (alpha.6 audit: the New
// expense form showed 9 headings, 6 of them empty — Currency, Taxes & charges,
// Advance payments, Totals, Exchange gain/loss, Accounting dimensions — and
// Time off showed an empty "Other details"). Each screen's field ALLOWLIST
// removes the fields but keeps every Section Break, because a layout field is
// kept by kind. This drops a Section Break that has no shown field before the
// next one. Rules: NN/g empty states; Apple HIG Writing (no crucial-looking
// text that says nothing).
import { test } from "node:test"
import assert from "node:assert/strict"

import { dropEmptySections } from "../visibleSections.js"

const sec = (label) => ({ fieldtype: "Section Break", fieldname: `s_${label}`, label })
const f = (name, extra = {}) => ({ fieldtype: "Data", fieldname: name, label: name, ...extra })
const col = { fieldtype: "Column Break", fieldname: "c1" }

const names = (fields) => fields.map((x) => x.fieldname)

test("a heading followed straight by another heading goes", () => {
	const out = dropEmptySections([f("a"), sec("Currency"), sec("Expenses"), f("b")], {})
	assert.deepEqual(names(out), ["a", "s_Expenses", "b"])
})

test("a heading at the end with nothing after it goes", () => {
	assert.deepEqual(names(dropEmptySections([f("a"), sec("Other details")], {})), ["a"])
})

test("a column break alone does not keep a section", () => {
	assert.deepEqual(names(dropEmptySections([sec("Totals"), col, sec("Next"), f("x")], {})), ["s_Next", "x"])
})

test("hidden fields do not keep a section", () => {
	// The hidden field itself stays in the list (the form still carries its
	// value); only its heading goes.
	const out = dropEmptySections([sec("Advance"), f("adv", { hidden: 1 }), sec("Items"), f("i")], {})
	assert.deepEqual(names(out), ["adv", "s_Items", "i"])
})

test("a read-only field with no value is not shown, so it does not keep a section", () => {
	const fields = [sec("Totals"), f("grand_total", { read_only: 1 }), sec("Items"), f("i")]
	assert.deepEqual(names(dropEmptySections(fields, {})), ["grand_total", "s_Items", "i"])
	assert.deepEqual(names(dropEmptySections(fields, { grand_total: 12.5 })), names(fields))
})

test("a Table is drawn by the form's own slot, so it keeps its section", () => {
	const fields = [sec("Expenses"), { fieldtype: "Table", fieldname: "expenses" }]
	assert.deepEqual(names(dropEmptySections(fields, {})), names(fields))
})

test("a section with a real field stays, in order", () => {
	const fields = [f("leave_type"), sec("Dates"), f("from_date"), f("to_date"), sec("Approval"), f("leave_approver")]
	assert.deepEqual(names(dropEmptySections(fields, {})), names(fields))
})

test("the form's own read-only decision is used (a sent request is read-only)", () => {
	const fields = [sec("Reason"), f("explanation"), sec("Items"), f("i", { read_only: 0 })]
	const allReadOnly = () => true
	assert.deepEqual(names(dropEmptySections(fields, { i: "x" }, allReadOnly)), ["explanation", "s_Items", "i"])
})
