const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const dir = __dirname;

test("Desk puts manager and HR approval fields below Approval Status", () => {
	const meta = JSON.parse(fs.readFileSync(path.join(dir, "expense_claim.json"), "utf8"));
	const order = meta.field_order;
	assert.ok(order.indexOf("approval_status") < order.indexOf("approval_history"));
	assert.ok(order.indexOf("approval_history") < order.indexOf("currency_section"));
	assert.equal(meta.fields.find((field) => field.fieldname === "approval_history")?.fieldtype, "HTML");
});

test("Desk reads decision names, escapes them, and shows HR waiting until approved", () => {
	const handlers = {};
	let markup = "";
	let method = "";
	const sandbox = {
		__: (text) => text,
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value.replaceAll("<", "&lt;").replaceAll(">", "&gt;") },
			call(options) {
				method = options.method;
				options.callback({ message: { manager: "Manager <One>", hr: null } });
			},
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	const frm = {
		doc: { name: "HR-EXP-1", approval_status: "Waiting for HR", docstatus: 0 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	};
	handlers["Expense Claim"].show_approval_names(frm);
	assert.equal(method, "hrms.api.request_history.get_expense_claim_approvers");
	assert.match(markup, /Manager approved by/);
	assert.match(markup, /HR approved by/);
	assert.match(markup, /Manager &lt;One&gt;/);
	assert.doesNotMatch(markup, /Manager <One>/);
	assert.match(markup, /Waiting for HR/);
});

test("Desk shows the actual HR approver after final approval", () => {
	const handlers = {};
	let markup = "";
	const sandbox = {
		__: (text) => text,
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value },
			call(options) { options.callback({ message: { manager: "Manager Name", hr: "HR Name" } }); },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	handlers["Expense Claim"].show_approval_names({
		doc: { name: "HR-EXP-1", approval_status: "Approved", docstatus: 1 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	});
	assert.match(markup, /Manager Name/);
	assert.match(markup, /HR Name/);
	assert.doesNotMatch(markup, /Waiting for HR/);
});

test("Desk labels a single-step approver without guessing their role", () => {
	const handlers = {};
	let markup = "";
	const sandbox = {
		__: (text) => text,
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value },
			call(options) { options.callback({ message: { manager: null, hr: null, direct: "One Approver" } }); },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	handlers["Expense Claim"].show_approval_names({
		doc: { name: "HR-EXP-OLD", approval_status: "Approved", docstatus: 1 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	});
	assert.match(markup, /Approved by/);
	assert.match(markup, /One Approver/);
	assert.doesNotMatch(markup, /Manager approved by/);
});

test("Desk explains a skipped manager step when a claim goes directly to HR", () => {
	const handlers = {};
	let markup = "";
	const sandbox = {
		__: (text) => text,
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value },
			call(options) { options.callback({ message: { manager: null, hr: null, direct: null } }); },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	handlers["Expense Claim"].show_approval_names({
		doc: { name: "HR-EXP-1", approval_status: "Waiting for HR", docstatus: 0 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	});
	assert.match(markup, /No manager approval/);
	assert.match(markup, /Waiting for HR/);
});

test("an older approval response cannot overwrite a newer refresh", () => {
	const handlers = {};
	const callbacks = [];
	let markup = "";
	const sandbox = {
		__: (text) => text,
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value },
			call(options) { callbacks.push(options.callback); },
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	const frm = {
		doc: { name: "HR-EXP-1", approval_status: "Waiting for HR", docstatus: 0 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	};
	handlers["Expense Claim"].show_approval_names(frm);
	handlers["Expense Claim"].show_approval_names(frm);
	callbacks[1]({ message: { manager: "Newest Manager", hr: null } });
	callbacks[0]({ message: { manager: "Stale Manager", hr: null } });
	assert.match(markup, /Newest Manager/);
	assert.doesNotMatch(markup, /Stale Manager/);
});

// Owner, 13 Nov 2026: the claim says on what date its manager approved it.
test("Desk shows the date the manager approved, and the date HR approved", () => {
	const handlers = {};
	let markup = "";
	const sandbox = {
		__: (text, args = []) => args.reduce((s, a, i) => s.replace(`{${i}}`, a), text),
		console: { info() {} },
		frappe: {
			provide() {},
			ui: { form: { on(doctype, events) { handlers[doctype] = events; } } },
			utils: { escape_html: (value) => value },
			datetime: { str_to_user: (value) => `user(${value})` },
			call(options) {
				options.callback({
					message: { manager: "Azhar", manager_on: "2026-11-12 09:15:00", hr: "HR Name", hr_on: "2026-11-13 10:00:00" },
				});
			},
		},
	};
	vm.runInNewContext(fs.readFileSync(path.join(dir, "expense_claim.js"), "utf8"), sandbox);
	const frm = {
		doc: { name: "HR-EXP-1", approval_status: "Approved", docstatus: 1 },
		fields_dict: { approval_history: { $wrapper: { html(value) { markup = value; } } } },
		is_new: () => false,
	};
	handlers["Expense Claim"].show_approval_names(frm);
	assert.match(markup, /Azhar/);
	assert.match(markup, /on user\(2026-11-12 09:15:00\)/);
	assert.match(markup, /on user\(2026-11-13 10:00:00\)/);
});
