const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

test("Employee Number is visible but read-only on an existing naming-series Employee", () => {
	let employeeForm;
	const sandbox = {
		__: (text) => text,
		frappe: {
			ui: { form: { on(doctype, events) { if (doctype === "Employee") employeeForm = events; } } },
			db: { get_single_value() { return { then(callback) { callback("Naming Series"); } }; } },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "employee.js"), "utf8"), sandbox);
	const metadata = { employee_number: { hidden: 1, read_only: 0 }, holiday_list: { hidden: 0 } };
	const frm = {
		doc: { name: "HR-EMP-001", company: "Example" },
		fields_dict: { employee_number: {} },
		set_query() {},
		set_df_property(fieldname, property, value) { metadata[fieldname][property] = value; },
		toggle_display() {},
		is_new() { return false; },
	};
	employeeForm.refresh(frm);
	assert.equal(metadata.employee_number.hidden, 0);
	assert.equal(metadata.employee_number.read_only, 1);
});

test("new naming-series Employees keep the unused number field hidden", () => {
	let employeeForm;
	const sandbox = {
		__: (text) => text,
		frappe: {
			ui: { form: { on(doctype, events) { if (doctype === "Employee") employeeForm = events; } } },
			db: { get_single_value() { return { then(callback) { callback("Naming Series"); } }; } },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "employee.js"), "utf8"), sandbox);
	const metadata = { employee_number: { hidden: 1 }, holiday_list: { hidden: 0 } };
	const frm = {
		doc: { name: "new-employee-1", company: "Example" },
		fields_dict: { employee_number: {} },
		set_query() {},
		set_df_property(fieldname, property, value) { metadata[fieldname][property] = value; },
		toggle_display() {},
		is_new() { return true; },
	};
	employeeForm.refresh(frm);
	assert.equal(metadata.employee_number.hidden, 1);
});

test("saved Employee Number records show their number without allowing an ID mismatch", () => {
	let employeeForm;
	const sandbox = {
		__: (text) => text,
		frappe: {
			ui: { form: { on(doctype, events) { if (doctype === "Employee") employeeForm = events; } } },
			db: { get_single_value() { return { then(callback) { callback("Employee Number"); } }; } },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "employee.js"), "utf8"), sandbox);
	const metadata = { employee_number: { hidden: 1, read_only: 0 }, holiday_list: { hidden: 0 } };
	const frm = {
		doc: { name: "HR-EMP-001", company: "Example" },
		fields_dict: { employee_number: {} },
		set_query() {},
		set_df_property(fieldname, property, value) { metadata[fieldname][property] = value; },
		toggle_display() {},
		is_new() { return false; },
	};
	employeeForm.refresh(frm);
	assert.equal(metadata.employee_number.hidden, 0);
	assert.equal(metadata.employee_number.read_only, 1);
});

test("a reused Employee form resets visibility and editability for each mode", () => {
	let employeeForm;
	let namingMode = "Naming Series";
	const sandbox = {
		__: (text) => text,
		frappe: {
			ui: { form: { on(doctype, events) { if (doctype === "Employee") employeeForm = events; } } },
			db: { get_single_value() { return { then(callback) { callback(namingMode); } }; } },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "employee.js"), "utf8"), sandbox);
	const metadata = { employee_number: { hidden: 1, read_only: 0 }, holiday_list: { hidden: 0 } };
	let isNew = false;
	const frm = {
		doc: { name: "HR-EMP-001", company: "Example" },
		fields_dict: { employee_number: {} },
		set_query() {},
		set_df_property(fieldname, property, value) { metadata[fieldname][property] = value; },
		toggle_display() {},
		is_new() { return isNew; },
	};
	employeeForm.refresh(frm);
	assert.deepEqual(metadata.employee_number, { hidden: 0, read_only: 1 });
	namingMode = "Employee Number";
	employeeForm.refresh(frm);
	assert.deepEqual(metadata.employee_number, { hidden: 0, read_only: 1 });
	namingMode = "Naming Series";
	isNew = true;
	employeeForm.refresh(frm);
	assert.deepEqual(metadata.employee_number, { hidden: 1, read_only: 0 });
	namingMode = "Employee Number";
	employeeForm.refresh(frm);
	assert.deepEqual(metadata.employee_number, { hidden: 0, read_only: 0 });
});
