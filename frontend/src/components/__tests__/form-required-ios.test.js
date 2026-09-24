// alpha.7 B14: no red asterisks (iOS forms have none). A required row that
// is still empty says "Required" in grey where its value goes, for every
// kind of row, text or menu or picker.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const field = read("../FormField.vue")
const css = read("../../theme/glass-components.css")

test("no asterisk on a required label", () => {
	assert.doesNotMatch(field, /g-form-row__label--required/)
	assert.doesNotMatch(css, /g-form-row__label--required/)
})

test("menus and pickers show Required/Optional while empty", () => {
	const select = field.slice(field.indexOf("<GSelect"), field.indexOf("/>", field.indexOf("<GSelect")))
	assert.match(select, /:placeholder="\$attrs\.placeholder \|\| rowPlaceholder"/)
	const link = field.slice(field.indexOf("<Link"), field.indexOf("/>", field.indexOf("<Link")))
	assert.match(link, /:placeholder="\$attrs\.placeholder \|\| rowPlaceholder"/)
})
