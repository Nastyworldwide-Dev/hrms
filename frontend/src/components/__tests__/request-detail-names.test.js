// alpha.9 D10/D11 (measured 25 Sep 2026 on every request type, as the
// approver): a saved request read "Who HR-EMP-00009" — an employee ID, which
// the owner ruled never reaches a person — and "Company Nadi W0 A" on the
// employee's OWN request, which tells them nothing they do not know.
// FormView draws every request detail, so the rule lives there once.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const view = read("../FormView.vue")
const field = read("../FormField.vue")
const link = read("../Link.vue")

test("the person row shows the stored name, never the ID", () => {
	// every request doctype stores employee_name beside employee
	assert.match(view, /:display="displayFor\(field\)"/)
	assert.match(view, /employee: \(model\) => model\.employee_name/)
	assert.match(field, /:display="props\.display"/)
	assert.match(link, /display: \{ type: String, default: "" \}/)
	assert.match(link, /if \(props\.display\) return props\.display/)
})

test("Company is not drawn on the viewer's own request", () => {
	assert.match(view, /OWN_REQUEST_NOISE = \["company"\]/)
	assert.match(view, /formModel\.value\?\.employee === currentEmployee\?\.data\?\.name/)
})

test("a row label keeps its one line beside a short value (D14)", () => {
	// Measured on 36 screens at 402 and 320 pt: the 45% cap broke 12 labels
	// ("Hours from check-ins", "Shift reminders", "Day you worked") onto two
	// lines beside a one-digit value or a switch; at 70% one remains, a long
	// question beside a picker on the narrowest phone.
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-form-row__label \{\s*flex: 0 1 auto;[^}]*max-width: 70%;/)
})
