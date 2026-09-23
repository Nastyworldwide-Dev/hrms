// The Desk filter for Staff Without A Shift: registered under the report's
// exact name (a mismatch loads the page with no filters and no error) and
// offers the company filter the server fences on.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import vm from "node:vm"

const here = (p) => fileURLToPath(new URL(p, import.meta.url))
const spec = JSON.parse(readFileSync(here("./staff_without_a_shift.json"), "utf8"))

test("the filter script registers under the report's own name, with a company filter", () => {
	const frappe = { query_reports: {} }
	vm.runInNewContext(readFileSync(here("./staff_without_a_shift.js"), "utf8"), {
		frappe,
		__: (s) => s,
	})
	const registered = frappe.query_reports[spec.report_name]
	assert.ok(registered, `registered as "${spec.report_name}"`)
	// the arrays were built in another vm context, so compare their text
	assert.equal(JSON.stringify(registered.filters.map((f) => [f.fieldname, f.options])), '[["company","Company"]]')
})
