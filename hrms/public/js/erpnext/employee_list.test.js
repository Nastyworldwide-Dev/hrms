const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function listSettings() {
	const sandbox = { __: (text) => text, frappe: { listview_settings: {} } };
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "employee_list.js"), "utf8"), sandbox);
	return sandbox.frappe.listview_settings.Employee;
}

test("every one of HR's five statuses has its own colour, Resigned in Left's grey", () => {
	const settings = listSettings();
	const colour = (status) => settings.get_indicator({ status })[1];
	assert.equal(colour("Active"), "green");
	assert.equal(colour("Resigned"), "gray");
	assert.equal(colour("Terminated"), "red");
	assert.equal(colour("Deceased"), "darkgrey");
	assert.equal(colour("Suspended"), "orange");
});

test("clicking the pill filters the list by that status", () => {
	assert.equal(listSettings().get_indicator({ status: "Resigned" })[2], "status,=,Resigned");
});
