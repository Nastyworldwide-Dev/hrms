// HR lists cost centers per company on an Expense Claim Type (owner, 14 Oct 2026):
// the Cost Center picker in that table offers only the row company's leaf cost centers.
// Run: node --test hrms/hr/doctype/expense_claim_type/expense_claim_type.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function refresh() {
	let handlers;
	const queries = {};
	const frm = {
		doc: {},
		fields_dict: { accounts: { grid: { get_field: () => ({}) } } },
		set_query: (field, table, fn) => (queries[`${table}.${field}`] = fn),
	};
	const sandbox = {
		locals: { "Expense Claim Type Cost Center": { r1: { company: "Shenzhen" } } },
		frappe: { ui: { form: { on: (_dt, h) => (handlers = h) } } },
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "expense_claim_type.js"), "utf8"), sandbox);
	handlers.refresh(frm);
	return queries;
}

test("the cost center picker offers only the row company's leaf, enabled cost centers", () => {
	const query = refresh()["cost_centers.cost_center"];
	assert.ok(query, "no query set on cost_centers.cost_center");
	assert.deepStrictEqual(
		JSON.parse(JSON.stringify(query({}, "Expense Claim Type Cost Center", "r1"))),
		{ filters: { company: "Shenzhen", is_group: 0, disabled: 0 } },
	);
});
