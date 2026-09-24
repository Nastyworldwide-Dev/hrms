// alpha.6 B1–B3: a form is an inset grouped list, not a stack of boxes.
//
// Measured before (alpha6-pages.md §F): six field looks on one form
// (48/0, 49/0, 64/0, 44/12, 48/12, 50/12 px height/radius), a checkbox for
// "Half day", labels above boxes. Apple HIG (Lists and tables, Toggles,
// Pickers; iOS Settings / Calendar "New Event"): one rounded group per section,
// rows with the label leading and the value trailing, hairlines inset to the
// text, a switch trailing its row, long text on its own row.
// Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const formView = read("../FormView.vue")
const formField = read("../FormField.vue")
const css = read("../../theme/glass-components.css")

test("FormView draws each section as one group (groupFields), not a stack of fields", () => {
	assert.match(formView, /groupFields\(/)
	assert.match(formView, /class="g-form-group"/)
})

test("the old square-box override is gone (it forced radius 0 on every form input)", () => {
	assert.doesNotMatch(formView, /border-radius:\s*0;/)
})

test("a Check field is a switch trailing its row, not a checkbox", () => {
	const at = formField.indexOf(`<template v-else-if="props.fieldtype === 'Check'">`)
	const check = formField.slice(at, at + 500)
	assert.match(check, /<GSwitch/)
	assert.doesNotMatch(check, /<GCheckbox/)
})

test("one row anatomy: label leading, control trailing, 44px minimum", () => {
	assert.match(css, /\.g-form-row\s*{[^}]*min-height:\s*var\(--g-touch-target-min\)/s)
	assert.match(css, /\.g-form-row__label\s*{/)
})

test("controls inside a group lose their own box (the group is the surface)", () => {
	assert.match(css, /\.g-form-group \.g-input,[^{]*{[^}]*border:\s*0;/s)
	assert.match(css, /\.g-form-group \.g-input,[^{]*{[^}]*background:\s*transparent/s)
})

test("hairlines are inset to the text, and the last row has none (HIG grouped list)", () => {
	assert.match(css, /\.g-form-row \+ \.g-form-row::before/)
})

// alpha.7 0.1 (owner's live Overtime shot, 25 Sep): "Could not check overtime…"
// wrapped one word per line inside the Hours value, the row grew 43 -> 87 pt.
// `.g-form-row > :not(.g-form-row__label):not(.g-form-row__switch)` is
// specificity (0,3,0) and gave the error `flex: 1 1 0`; the old error rule was
// (0,2,0) and lost. The error must be a full-width line UNDER the row.
test("a field error takes the full row width under the value (beats the child rule)", () => {
	assert.match(css, /\.g-form-row\.g-form-row--error\s*>\s*\.g-field-error\s*{[^}]*flex:\s*0 0 100%/s)
})
