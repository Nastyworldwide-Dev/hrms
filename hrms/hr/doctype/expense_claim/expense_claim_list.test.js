// Expense Claim has two parts, the decision (approval_status) and the money (status). Desk says what Nadi
// says: Waiting / Approved · unpaid / Paid / Rejected / Cancelled (owner, 5 Oct 2026).
// Run: node --test hrms/hr/doctype/expense_claim/expense_claim_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load() {
	const settings = {};
	const sandbox = { __: (t) => t, frappe: { listview_settings: settings } };
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "expense_claim_list.js"), "utf8"), sandbox);
	return settings["Expense Claim"];
}
const word = (doc) => [...load().get_indicator(doc)];

test("a claim nobody has decided says Waiting", () => {
	assert.deepStrictEqual(word({ docstatus: 0, status: "Draft", approval_status: "Draft" }), ["Waiting", "orange", "docstatus,=,0"]);
});

test("approved but not paid says Approved · unpaid, the same words as Nadi", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Unpaid", approval_status: "Approved" }), ["Approved · unpaid", "blue", "approval_status,=,Approved"]);
	// nothing sanctioned: set_status leaves the stored status "Submitted", and the pill must still list it
	assert.deepStrictEqual(word({ docstatus: 1, status: "Submitted", approval_status: "Approved" }), ["Approved · unpaid", "blue", "approval_status,=,Approved"]);
});

test("paid says Paid", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Paid", approval_status: "Approved" }), ["Paid", "green", "status,=,Paid"]);
});

test("rejected says Rejected, and a click filters on the stored decision", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Rejected", approval_status: "Rejected" }), ["Rejected", "red", "approval_status,=,Rejected"]);
});

test("cancelled says Cancelled", () => {
	assert.deepStrictEqual(word({ docstatus: 2, status: "Cancelled", approval_status: "Approved" }), ["Cancelled", "red", "docstatus,=,2"]);
});

test("a decision saved in Desk but never submitted still says Waiting, never Approved", () => {
	assert.strictEqual(word({ docstatus: 0, status: "Draft", approval_status: "Approved" })[0], "Waiting");
});

test("the doctype no longer carries Frappe's own states, which would outrank this rule", () => {
	const json = JSON.parse(fs.readFileSync(path.join(__dirname, "expense_claim.json"), "utf8"));
	assert.deepStrictEqual(json.states, []);
});
