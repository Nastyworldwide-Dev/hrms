// A form is an inset grouped list (Apple HIG Lists and tables; iOS Settings and
// Calendar "New Event"): each section is ONE group of rows under a small grey
// heading, not a stack of boxed fields (alpha.6 B2, rulebook K2 / R1 / R4).
// groupFields turns the doctype's flat field list into those groups.
import { test } from "node:test"
import assert from "node:assert/strict"

import { groupFields } from "../formGroups.js"

const sec = (label) => ({ fieldtype: "Section Break", fieldname: `s_${label}`, label })
const f = (name, fieldtype = "Data") => ({ fieldtype, fieldname: name, label: name })
const shape = (groups) =>
	groups.map((g) => [g.label, g.segments.map((s) => (s.kind === "rows" ? s.fields.map((x) => x.fieldname) : `table:${s.field.fieldname}`))])

test("fields before the first heading form an unlabelled group", () => {
	assert.deepEqual(shape(groupFields([f("leave_type"), sec("Dates"), f("from"), f("to")])), [
		["", [["leave_type"]]],
		["Dates", [["from", "to"]]],
	])
})

test("column breaks are layout for a desktop grid and vanish", () => {
	const out = groupFields([f("a"), { fieldtype: "Column Break", fieldname: "c" }, f("b")])
	assert.deepEqual(shape(out), [["", [["a", "b"]]]])
})

test("a table splits its group: rows before, the table, rows after", () => {
	const out = groupFields([sec("Expenses"), f("x"), f("expenses", "Table"), f("y")])
	assert.deepEqual(shape(out), [["Expenses", [["x"], "table:expenses", ["y"]]]])
})

test("a heading with nothing under it makes no group", () => {
	assert.deepEqual(shape(groupFields([sec("Empty"), sec("Real"), f("a")])), [["Real", [["a"]]]])
})

test("nothing in, nothing out", () => {
	assert.deepEqual(groupFields([]), [])
	assert.deepEqual(groupFields(undefined), [])
})
