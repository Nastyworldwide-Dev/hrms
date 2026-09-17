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

// --- the same day, reached from the row instead of the punches --------------
// Owner, 17 Sep 2026: "each of these pages must have relinking,pairing button".
// HR lands here as often as on Employee Checkin — a duplicated day is visible
// as two rows on THIS list — so the day's fix screen opens from here too, on
// the employee and date of the ticked row.
const { loadDesk, fakeListview } = require("../../../tests/js/desk_list_harness.js");

const BUNDLE = path.join(__dirname, "..", "..", "..", "public", "js", "fix_day.bundle.js");

function controls(options) {
	const { settings, sandbox } = loadDesk(
		[BUNDLE, path.join(__dirname, "attendance_list.js")],
		options,
	);
	const listview = fakeListview([
		{ name: "HR-ATT-2026-15657", employee: "HR-EMP-00069", attendance_date: "2026-09-04" },
	]);
	settings["Attendance"].onload.call(settings["Attendance"], listview);
	return { listview, labels: listview.page.buttons.map((b) => b.label), sandbox };
}

test("HR finds Fix day on the Attendance list", () => {
	assert.ok(controls().labels.includes("Fix day"));
});

test("the list keeps Mark Attendance", () => {
	assert.ok(controls().labels.includes("Mark Attendance"));
});

test("a non-HR user is not offered the fix screen", () => {
	assert.ok(!controls({ has_role: false }).labels.includes("Fix day"));
});

test("the employee rides along, or the row cannot name its own day", () => {
	assert.ok(SETTINGS.add_fields.includes("employee"));
});

test("the ticked row opens its own employee-day", () => {
	const { listview, sandbox } = controls();
	let opened = null;
	sandbox.hrms.fix_day.open = (options) => (opened = options);
	listview.page.buttons.find((b) => b.label === "Fix day").handler();
	assert.deepStrictEqual(
		{ employee: opened.employee, date: opened.date },
		{ employee: "HR-EMP-00069", date: "2026-09-04" },
	);
});
