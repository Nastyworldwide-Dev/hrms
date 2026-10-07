// design/token-collapses.md ("Misuse found", 7 Oct 2026): a few places inside a
// sheet (GModal) drew with the PAGE ground or the CARD surface. In dark the page
// ground is #000 (a black slab on the #1C1C1E sheet) and the card surface is
// #1C1C1E (invisible on the sheet, contrast 1.00). Inside a sheet the right
// tokens are bg-sheet-bg (the sheet's ground) and bg-sheet-cell (a cell on it).
// Also: the picked-option tick used the brand fill colour as a mark on light
// (1.18:1 on white); a mark takes --g-accent-ink.
// Approvals.vue's .g-approvals__bar is NOT here: it is an open owner question.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const template = (src) => src.split("<script")[0]
const lineOf = (src, n) => src.split("\n")[n - 1]

test("StrictRejectionDialog: the sheet body is the sheet's ground, not the page's", () => {
	const src = read("../StrictRejectionDialog.vue")
	assert.match(src, /<GModal\b/)
	const body = lineOf(src, 3)
	assert.match(body, /\bbg-sheet-bg\b/)
	assert.doesNotMatch(body, /\bbg-bg\b/)
	assert.doesNotMatch(template(src), /\bbg-bg\b/)
})

test("ExpenseTaxesTable: the Add tax sheet uses the sheet's ground and cell", () => {
	const src = read("../ExpenseTaxesTable.vue")
	const tpl = template(src)
	const modal = tpl.slice(tpl.indexOf("<GModal"), tpl.indexOf("</GModal>"))
	assert.match(modal, /class="bg-sheet-bg w-full flex flex-col pb-5"/)
	assert.doesNotMatch(modal, /\bbg-ground\b/)
	const style = src.split("<style")[1]
	assert.match(style, /background-color: var\(--g-sheet-cell\);/)
	assert.doesNotMatch(style, /--g-glass-fill-fallback/)
})

test("WorkflowActionSheet: the bar inside the sheet is the sheet's ground, the page bar keeps the page ground", () => {
	const src = read("../WorkflowActionSheet.vue")
	const [formBar, sheetBar] = [lineOf(src, 6), lineOf(src, 7)]
	assert.match(formBar, /\bbg-ground\b/)
	assert.match(sheetBar, /\bbg-sheet-bg\b/)
	assert.doesNotMatch(sheetBar, /\bbg-ground\b/)
})

test("FormattedField: the read-only text block (shown in a sheet) is a sheet cell", () => {
	const src = read("../FormattedField.vue")
	const block = lineOf(src, 28)
	assert.match(block, /\bbg-sheet-cell\b/)
	assert.doesNotMatch(block, /\bbg-surface\b/)
})

test("TeamRoster: the Assign shift date inputs are sheet cells; the roster grid keeps the card surface", () => {
	const src = read("../../views/team/TeamRoster.vue")
	const tpl = template(src)
	const assign = tpl.slice(tpl.indexOf("<GModal"), tpl.indexOf("</GModal>"))
	assert.match(assign, /Assign shift/)
	const dates = assign.match(/type="date"[\s\S]*?\/>/g) ?? []
	assert.equal(dates.length, 2)
	for (const input of dates) {
		assert.match(input, /\bbg-sheet-cell\b/)
		assert.doesNotMatch(input, /\bbg-surface\b/)
	}
	// the shift-on cell of the page grid is not in a sheet and stays a card surface
	assert.match(lineOf(src, 68), /'bg-surface'/)
})

// Rules of the hand-written stylesheet whose selector list holds `selector`.
function rulesFor(css, selector) {
	const bare = css.replace(/\/\*[\s\S]*?\*\//g, "")
	const out = []
	for (const [, sel, body] of bare.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
		if (sel.split(",").some((s) => s.trim() === selector)) out.push(body)
	}
	return out
}

test("glass-components.css: an attachment row inside a sheet is a sheet cell", () => {
	const css = read("../../theme/glass-components.css")
	const rules = rulesFor(css, ".g-sheet .g-attachment")
	assert.ok(rules.length > 0, ".g-sheet .g-attachment is in the sheet-cell override list")
	assert.ok(
		rules.some((body) => /background:\s*var\(--g-sheet-cell\);/.test(body)),
		"and that list sets --g-sheet-cell"
	)
})

test("glass-components.css: the picked-option tick is an accent mark, not the brand fill", () => {
	const css = read("../../theme/glass-components.css")
	const rules = rulesFor(css, ".g-linkpick__tick")
	assert.equal(rules.length, 1)
	assert.match(rules[0], /color:\s*var\(--g-accent-ink\);/)
	assert.doesNotMatch(rules[0], /--g-brand\b/)
})
