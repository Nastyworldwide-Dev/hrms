// One word per state in Desk, as in Nadi. Runs the REAL bundle and the REAL list scripts in one
// sandbox, in Desk's order (bundle at boot, list script when the list opens), then asks each list
// what it shows. Run: node --test hrms/public/js/request_status.bundle.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "..", "..");
const LISTS = {
	"Leave Application": "hr/doctype/leave_application/leave_application_list.js",
	"OT Request": "hr/doctype/ot_request/ot_request_list.js",
	"Shift Request": "hr/doctype/shift_request/shift_request_list.js",
	"Attendance Request": "hr/doctype/attendance_request/attendance_request_list.js",
	"Replacement Leave Claim": "hr/doctype/replacement_leave_claim/replacement_leave_claim_list.js",
	"Compensatory Leave Request": "hr/doctype/compensatory_leave_request/compensatory_leave_request_list.js",
};

function desk() {
	const hrms = {};
	const sandbox = {
		hrms,
		__: (text) => text,
		console: { info() {} },
		format_number: (v, _f, d) => Number(v).toFixed(d),
		frappe: {
			listview_settings: {},
			meta: { docfield_map: {} },
			provide: (ns) => String(ns).split(".").reduce((o, k) => (o[k] = o[k] || {}), sandbox),
			form: { formatters: { _right: (v) => v } },
		},
	};
	// ONE context for the whole page, as in Desk: the bundle runs at boot, each list script when its
	// list opens. (A fresh context per file would give each its own `hrms`.)
	const context = vm.createContext(sandbox);
	vm.runInContext(fs.readFileSync(path.join(__dirname, "request_status.bundle.js"), "utf8"), context);
	for (const file of Object.values(LISTS)) {
		vm.runInContext(fs.readFileSync(path.join(ROOT, file), "utf8"), context);
	}
	return sandbox.frappe.listview_settings;
}

const word = (settings, doctype, doc) => settings[doctype].get_indicator(doc)[0];

test("every request list says Waiting for a request nobody has decided", () => {
	const settings = desk();
	for (const doctype of Object.keys(LISTS)) {
		assert.strictEqual(word(settings, doctype, { docstatus: 0, status: "Open" }), "Waiting", doctype);
		assert.strictEqual(word(settings, doctype, { docstatus: 0, status: "Draft" }), "Waiting", doctype);
	}
});

test("a decision saved in Desk but never submitted still says Waiting, never Approved", () => {
	const settings = desk();
	assert.strictEqual(word(settings, "Leave Application", { docstatus: 0, status: "Approved" }), "Waiting");
	assert.strictEqual(word(settings, "Shift Request", { docstatus: 0, status: "Rejected" }), "Waiting");
});

test("a submitted request says what was decided; submitting an old Open row means approved", () => {
	const settings = desk();
	for (const doctype of Object.keys(LISTS)) {
		assert.strictEqual(word(settings, doctype, { docstatus: 1, status: "Approved" }), "Approved", doctype);
		assert.strictEqual(word(settings, doctype, { docstatus: 1, status: "Rejected" }), "Rejected", doctype);
		assert.strictEqual(word(settings, doctype, { docstatus: 1, status: "Open" }), "Approved", doctype);
	}
});

test("a cancelled request says Cancelled", () => {
	const settings = desk();
	assert.strictEqual(word(settings, "Leave Application", { docstatus: 2, status: "Cancelled" }), "Cancelled");
});

test("the colours: waiting orange, approved green, rejected and cancelled red", () => {
	const settings = desk();
	const colour = (doc) => settings["Leave Application"].get_indicator(doc)[1];
	assert.strictEqual(colour({ docstatus: 0 }), "orange");
	assert.strictEqual(colour({ docstatus: 1, status: "Approved" }), "green");
	assert.strictEqual(colour({ docstatus: 1, status: "Rejected" }), "red");
	assert.strictEqual(colour({ docstatus: 2 }), "red");
});

test("the filter a click on the label applies matches the stored value", () => {
	const settings = desk();
	assert.strictEqual(settings["Leave Application"].get_indicator({ docstatus: 0 })[2], "docstatus,=,0");
	assert.strictEqual(settings["Leave Application"].get_indicator({ docstatus: 1, status: "Rejected" })[2], "status,=,Rejected");
});

test("the OT list keeps its 2-decimal hours formatter next to the new indicator", () => {
	const settings = desk();
	assert.strictEqual(typeof settings["OT Request"].formatters.claimed_hours, "function");
});

test("the bundle is loaded at boot and assigns no listview_settings itself", () => {
	const hooks = fs.readFileSync(path.join(ROOT, "hooks.py"), "utf8");
	assert.match(hooks, /"request_status\.bundle\.js"/);
	assert.doesNotMatch(fs.readFileSync(path.join(__dirname, "request_status.bundle.js"), "utf8").replace(/\/\/.*$/gm, ""), /listview_settings/);
});
