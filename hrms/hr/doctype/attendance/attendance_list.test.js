// The attendance list must show which shift a day was marked under and who
// owns it, and keep its status colours.
// Run: node --test hrms/hr/doctype/attendance/attendance_list.test.js
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
			ui: { Dialog: function () {} },
			datetime: { get_today: () => "2026-09-10" },
		},
		__: (s) => s,
		moment: Object.assign(
			() => ({ startOf: () => ({ subtract: () => ({}) }), toDate: () => new Date() }),
			{},
		),
	};
	vm.runInNewContext(fs.readFileSync(file, "utf8"), sandbox);
	return settings;
}

const SETTINGS = loadSettings(path.join(__dirname, "attendance_list.js"))["Attendance"];

test("shift, owner and hours ride along with the list", () => {
	for (const field of ["shift", "auto_attendance", "working_hours"]) {
		assert.ok(SETTINGS.add_fields.includes(field), `add_fields missing: ${field}`);
	}
});

test("status drives the colour", () => {
	assert.strictEqual(SETTINGS.get_indicator({ status: "Present" })[1], "green");
	assert.strictEqual(SETTINGS.get_indicator({ status: "Absent" })[1], "red");
	assert.strictEqual(SETTINGS.get_indicator({ status: "Half Day" })[1], "orange");
});

test("a day HR keyed by hand is told apart from the job's own", () => {
	const manual = SETTINGS.get_indicator({ status: "Present", auto_attendance: 0 });
	const job = SETTINGS.get_indicator({ status: "Present", auto_attendance: 1 });
	assert.notStrictEqual(manual[0], job[0]);
	assert.match(manual[0], /HR|manual|by hand/i);
});
