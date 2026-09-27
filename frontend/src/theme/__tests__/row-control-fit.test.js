// alpha.14 I and J (27 Sep 2026 sweep, installed-iPhone profile):
//  J "What are you reporting?  Requirec" — the picker in a form row was sized
//    to its text (89 pt) and its trailing chevron is drawn inside that box,
//    over the last letter. A picker's value ends before its chevron and a too
//    long value ends in "…", never a cut letter.
//  I "Hours  Required ▮" — WebKit draws a number field's spin buttons, a stray
//    block after the placeholder. iOS has no stepper there; the keypad is it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const root = postcss.parse(readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8"))
function decls(selector) {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(selector)) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	return out
}

test("a picker in a row never draws its chevron over its value", () => {
	const d = decls(".g-form-group .g-select__native")
	assert.equal(d["padding-right"], "24px") // 16 pt chevron + 8
	assert.equal(d["box-sizing"], "border-box")
	assert.equal(d["text-overflow"], "ellipsis")
	assert.equal(d["min-width"], "calc(24px + 5ch)")
})

test("no number field in a form draws spin buttons", () => {
	assert.equal(decls(".g-form-group input[type=\"number\"]")["appearance"], "textfield")
	const spin = decls(".g-form-group input[type=\"number\"]::-webkit-inner-spin-button")
	assert.equal(spin["-webkit-appearance"], "none")
})

// Measured: "What are you reporting?" is 193 pt of text but its label box grew
// to 237 (`.g-form-row > .g-form-row__label { flex: 1 0 auto }`), leaving the
// picker 89 pt for a 95 pt value. A label is its text; the control gets the rest.
test("a row label does not grow past its text", () => {
	assert.equal(decls(".g-form-row > .g-form-row__label")["flex"], "0 1 auto")
})
