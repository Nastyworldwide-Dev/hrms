// Mandatory fields every FormView-driven form must satisfy (static audit,
// 15 Sep 2026).
//
// A PWA form is built from hrms.api.get_doctype_fields — the doctype's own
// field list — then the view filters and hides fields for the phone. Two
// refusals this week came from that gap: Expense Claim's posting_date sits
// past the one tab the form renders, and Shift Request's company was
// filtered out on create; both are reqd on the doctype, so the server refused
// the insert with "Value missing for …" and the employee saw an error with no
// field to fill in.
//
// For every <FormView doctype="…"> this lists each reqd field of the doctype
// JSON and proves ONE of:
//   rendered        — a supported fieldtype the view neither filters nor hides
//   client-seeded   — the view's model seeds it or sets field.default
//   server-set      — the name is a naming series, the controller sets the
//                      field itself, or the view drops the key entirely and
//                      the doctype JSON carries a default for it
// A reqd field with none of those is a gap: the insert can only fail.
// Forms with no create route (Shift Assignment: detail only) never insert.
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { HRMS_PY, rel, routeTable, sourceFiles, scriptText, templateText } from "./_lib.mjs"

// The server's own allowlist of renderable field types (hrms/api/__init__.py).
const api = readFileSync(join(HRMS_PY, "api", "__init__.py"), "utf8")
const SUPPORTED = new Set([...api.match(/SUPPORTED_FIELD_TYPES = \[([\s\S]*?)\]/)[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]))

function doctypeJson(doctype) {
	const snake = doctype.toLowerCase().replace(/\s+/g, "_")
	for (const module of readdirSync(HRMS_PY)) {
		const path = join(HRMS_PY, module, "doctype", snake, `${snake}.json`)
		if (existsSync(path)) return { json: JSON.parse(readFileSync(path, "utf8")), dir: join(HRMS_PY, module, "doctype", snake), snake }
	}
	return null
}

// Controller text plus every hrms.overrides helper it imports.
function controllerText(dt) {
	const path = join(dt.dir, `${dt.snake}.py`)
	if (!existsSync(path)) return ""
	let text = readFileSync(path, "utf8")
	for (const m of text.matchAll(/^from (hrms\.[\w.]+) import/gm)) {
		const helper = join(HRMS_PY, "..", ...m[1].split(".")) + ".py"
		if (existsSync(helper)) text += "\n" + readFileSync(helper, "utf8")
	}
	return text
}

// What the view does to the field list: string literals in the transform's
// filter arrays, `field.hidden = true` by name, tab slicing, model seeds.
function viewShape(file) {
	const script = scriptText(file)
	const excluded = new Set()
	// every string literal inside the formFields transform / getFilteredFields body
	const transform = script.match(/transform\(data\)\s*\{([\s\S]*?)\n\t\},?\n/)?.[1] || ""
	const filterFns = [...script.matchAll(/function getFilteredFields\(fields\)\s*\{([\s\S]*?)\n\}/g)].map((m) => m[1])
	const constArrays = [...script.matchAll(/^const [A-Z_]+ = \[([\s\S]*?)\]/gm)].map((m) => m[1])
	for (const body of [transform, ...filterFns, ...constArrays])
		for (const m of body.matchAll(/["']([a-z_0-9]+)["']/g)) excluded.add(m[1])
	const hidden = new Set([...script.matchAll(/fieldname === ["'](\w+)["']\) field\.hidden = true/g)].map((m) => m[1]))
	const defaults = new Set([...script.matchAll(/fieldname === ["'](\w+)["']\) field\.default/g)].map((m) => m[1]))
	// model seeds: `const x = ref({ a: ..., b: ... })` keys, and `x.value.f = …`
	const seeds = new Set()
	const model = script.match(/= ref\(\{([\s\S]*?)\n\}\)/)
	if (model) for (const m of model[1].matchAll(/^\s*(\w+):/gm)) seeds.add(m[1])
	for (const m of script.matchAll(/\.value\.(\w+) = /g)) seeds.add(m[1])
	const tpl = templateText(file)
	const tabs = script.match(/const tabs = \[([\s\S]*?)\]/)?.[1]
	const lastField = tabs ? [...tabs.matchAll(/lastField: "(\w+)"/g)].map((m) => m[1]).pop() : null
	const doctype = tpl.match(/<FormView[\s\S]*?doctype="([^"]+)"/)?.[1]
	return { doctype, excluded, hidden, defaults, seeds, lastField }
}

const forms = sourceFiles()
	.filter((f) => f.endsWith(".vue") && /<FormView[\s\S]*?doctype="/.test(templateText(f)))
	.map((f) => ({ file: f, ...viewShape(f) }))

test("every FormView-driven form is found with its doctype", () => {
	assert.ok(forms.length >= 7, `only ${forms.length} forms found`)
	for (const f of forms) assert.ok(f.doctype, `${rel(f.file)} has no doctype`)
})

const routeNames = new Set(routeTable().flat.map((r) => r.name).filter(Boolean))
const rows = []
const gaps = []
for (const form of forms) {
	const createRoute = `${form.doctype.replace(/\s+/g, "")}FormView`
	if (!routeNames.has(createRoute)) {
		rows.push(`${form.doctype.padEnd(24)} ${"(all)".padEnd(16)} detail-only form — no ${createRoute} route, never inserts`)
		continue
	}
	const dt = doctypeJson(form.doctype)
	if (!dt) {
		gaps.push(`${rel(form.file)}: doctype JSON for ${form.doctype} not found under hrms/`)
		continue
	}
	const controller = controllerText(dt)
	for (const field of dt.json.fields) {
		if (!field.reqd) continue
		const status = classify(form, field, dt.json.fields, controller)
		if (status.startsWith("GAP")) gaps.push(`${rel(form.file)} (${form.doctype}): reqd \`${field.fieldname}\` ${status.slice(6)}`)
		rows.push(`${form.doctype.padEnd(24)} ${field.fieldname.padEnd(16)} ${status}`)
	}
}

// Order matters: the strongest evidence first. A JSON `default` or `fetch_from`
// alone is NOT evidence — Shift Request's company had fetch_from
// employee.company and the server still refused "Value missing for Shift
// Request: Company" (hrms/overrides/employee_company_default.py): fetch_from
// is a Desk-form convenience, and a default is applied only to a key the
// client never sent.
export function classify(form, field, fields, controller) {
	const name = field.fieldname
	const fieldnames = fields.map((f) => f.fieldname)
	const cutoff = form.lastField ? fieldnames.indexOf(form.lastField) : Infinity
	const controllerSets = new RegExp(`(self|doc)\\.${name} = |def set_${name}\\(|set_${name}_from`).test(controller)
	if (name === "naming_series") return "server-set (naming series)"
	if (form.seeds.has(name) || form.defaults.has(name)) return "client-seeded"
	// the view filters the field out, so the key is ABSENT from the insert and
	// Document._set_defaults fills it from the JSON default
	if (form.excluded.has(name) && field.default) return `server-set (key absent, JSON default ${field.default})`
	if (SUPPORTED.has(field.fieldtype) && !form.excluded.has(name) && !form.hidden.has(name) && fieldnames.indexOf(name) <= cutoff)
		return "rendered"
	if (controllerSets) return "server-set (controller)"
	const why = !SUPPORTED.has(field.fieldtype)
		? `fieldtype ${field.fieldtype} not renderable`
		: form.excluded.has(name)
		? "filtered out by the view"
		: form.hidden.has(name)
		? "hidden by the view"
		: `past the last rendered tab field (${form.lastField})`
	const hint = field.fetch_from
		? `; fetch_from ${field.fetch_from} is not applied on insert`
		: field.default
		? `; JSON default ${field.default} only covers an absent key`
		: ""
	return `GAP — is neither rendered, seeded nor set by the controller — ${why}${hint}`
}

test("every reqd field of every form doctype is rendered, seeded or defaulted", () => {
	console.log("[forms] mandatory-field table:\n  " + rows.join("\n  "))
	assert.deepEqual(gaps, [], gaps.join("\n"))
})

test("the audit sees the Expense Claim posting_date seed and the Shift Request company default", () => {
	const expense = forms.find((f) => f.doctype === "Expense Claim")
	assert.ok(expense.seeds.has("posting_date"), "Expense Claim seeds posting_date in its model")
	assert.equal(expense.lastField, "taxes")
	const shift = doctypeJson("Shift Request")
	assert.match(controllerText(shift), /set_company_from_employee/)
})

test("the audit catches the Expense Claim posting_date and Shift Request company shapes", () => {
	const fields = [
		{ fieldname: "employee", fieldtype: "Link", reqd: 1 },
		{ fieldname: "expenses", fieldtype: "Table", reqd: 1 },
		{ fieldname: "taxes", fieldtype: "Table" },
		{ fieldname: "posting_date", fieldtype: "Date", reqd: 1, default: "Today" },
		{ fieldname: "company", fieldtype: "Link", reqd: 1, fetch_from: "employee.company" },
	]
	const bare = { excluded: new Set(["company"]), hidden: new Set(), defaults: new Set(), seeds: new Set(), lastField: "taxes" }
	assert.match(classify(bare, fields[3], fields, ""), /^GAP — .*past the last rendered tab field \(taxes\); JSON default Today/)
	assert.match(classify(bare, fields[4], fields, ""), /^GAP — .*filtered out by the view; fetch_from employee.company/)
	assert.equal(
		classify(bare, fields[4], fields, "from hrms.overrides.employee_company_default import set_company_from_employee"),
		"server-set (controller)"
	)
	const seeded = { ...bare, seeds: new Set(["posting_date"]) }
	assert.equal(classify(seeded, fields[3], fields, ""), "client-seeded")
	assert.equal(classify(bare, fields[0], fields, ""), "rendered")
})
