// The check-in list answers one question at a glance: did this punch count,
// and under which shift? These drive the real get_indicator, because the
// branch ORDER is the thing that can be wrong — a rejected punch that also
// carries an attendance link must read Rejected, not Counted.
// Run: node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadSettings(file) {
	const settings = {};
	const sandbox = {
		frappe: {
			listview_settings: settings,
			call: () => {},
			utils: {},
			perm: { has_perm: () => false },
		},
		__: (s) => s,
		moment: () => ({ startOf: () => ({}) }),
	};
	vm.runInNewContext(fs.readFileSync(file, "utf8"), sandbox);
	return settings;
}

const SETTINGS = loadSettings(path.join(__dirname, "employee_checkin_list.js"))[
	"Employee Checkin"
];
const label = (doc) => SETTINGS.get_indicator(doc)[0];

test("a punch linked to attendance reads Counted", () => {
	assert.strictEqual(label({ attendance: "HR-ATT-2026-00001" }), "Counted");
});

test("a punch with nothing yet reads Not counted yet", () => {
	assert.strictEqual(label({}), "Not counted yet");
});

test("a rejected punch reads Rejected even when it still carries a link", () => {
	assert.strictEqual(
		label({ remote_approval_status: "Rejected", attendance: "HR-ATT-2026-00001" }),
		"Rejected",
	);
});

test("a skipped punch reads Skipped, not Counted", () => {
	assert.strictEqual(
		label({ skip_auto_attendance: 1, attendance: "HR-ATT-2026-00001" }),
		"Skipped",
	);
});

test("a pending punch reads Awaiting approval", () => {
	assert.strictEqual(label({ remote_approval_status: "Pending" }), "Awaiting approval");
});

test("off-shift wins over everything: the job never reads that punch", () => {
	assert.strictEqual(
		label({
			offshift: 1,
			attendance: "HR-ATT-2026-00001",
			remote_approval_status: "Rejected",
		}),
		"Off-Shift",
	);
});

test("each indicator carries the filter that isolates it", () => {
	assert.strictEqual(SETTINGS.get_indicator({ attendance: "X" })[2], "attendance,is,set");
	assert.strictEqual(SETTINGS.get_indicator({})[2], "attendance,is,not set");
	assert.strictEqual(
		SETTINGS.get_indicator({ skip_auto_attendance: 1 })[2],
		"skip_auto_attendance,=,1",
	);
});

test("the fields behind the indicator are fetched", () => {
	// the list only loads what it shows or is told to add
	for (const field of [
		"skip_auto_attendance",
		"attendance",
		"shift",
		"remote_approval_status",
	]) {
		assert.ok(SETTINGS.add_fields.includes(field), `add_fields missing: ${field}`);
	}
});
