// alpha.12 keyboard (rules K21/K24; Apple, virtual-keyboards: "Use the
// keyboard layout guide to make the keyboard feel like an integrated part of
// your interface"; entering-data). Measured 26 Sep 2026: no field in the app
// set `inputmode` or `enterkeyhint`, so hours and money brought up the full
// letter keyboard on iPhone, and Return never said what it would do.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const input = read("../glass/GInput.vue")
const field = read("../FormField.vue")

test("GInput passes inputmode, enterkeyhint and autocomplete to the real input", () => {
	for (const attr of ["inputmode", "enterkeyhint", "autocomplete"]) {
		assert.match(input, new RegExp(`:${attr}="`), `${attr} reaches <input>`)
	}
})

test("hours and counts get the decimal pad; whole numbers the number pad", () => {
	const number = field.slice(field.indexOf("<!-- Float/Int field"), field.indexOf("<!-- Section Break -->"))
	assert.match(number, /:inputmode="numericMode"/)
	assert.match(field, /const numericMode = computed\(\(\) => \(props\.fieldtype === "Int" \? "numeric" : "decimal"\)\)/)
})

test("every text row says Return goes to the next field", () => {
	assert.match(field, /enterkeyhint="next"/)
})
