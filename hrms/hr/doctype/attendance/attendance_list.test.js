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

// --- the row is the symptom; the punches are where HR fixes it -------------
// Owner, 21 Sep 2026: the Fix Day tools live on the Employee Checkin list
// only. This list links there: "Punches" opens the check-in list on the
// ticked row's employee-day. The screen itself no longer opens from here.
const { loadDesk, fakeListview } = require("../../../tests/js/desk_list_harness.js");

const BUNDLE = path.join(__dirname, "..", "..", "..", "public", "js", "fix_day.bundle.js");

function controls(options, checked) {
	const { settings, sandbox, roles } = loadDesk(
		[BUNDLE, path.join(__dirname, "attendance_list.js")],
		options,
	);
	const routes = [];
	sandbox.frappe.set_route = (...route) => routes.push(JSON.parse(JSON.stringify(route)));
	const listview = fakeListview(
		checked || [
			{ name: "HR-ATT-2026-15657", employee: "HR-EMP-00069", attendance_date: "2026-09-04" },
		],
	);
	settings["Attendance"].onload.call(settings["Attendance"], listview);
	const punches = () => listview.page.buttons.find((b) => b.label === "Punches").handler();
	return {
		listview,
		labels: listview.page.buttons.map((b) => b.label),
		sandbox,
		roles,
		routes,
		punches,
		messages: sandbox.__messages,
	};
}

test("Fix day is gone from the Attendance list: the tool lives on the punches page", () => {
	assert.ok(!controls().labels.includes("Fix day"));
	assert.strictEqual(controls().sandbox.hrms.fix_day.from_attendance, undefined);
});

test("HR finds Punches, and it opens the check-in list on the ticked employee-day", () => {
	const { punches, routes } = controls();
	punches();
	assert.deepStrictEqual(routes, [
		[
			"List",
			"Employee Checkin",
			{ employee: "HR-EMP-00069", time: ["Between", ["2026-09-04", "2026-09-04"]] },
		],
	]);
});

test("Punches refuses rows of two people or two days", () => {
	const { punches, routes, messages } = controls(undefined, [
		{ name: "A", employee: "HR-EMP-00069", attendance_date: "2026-09-04" },
		{ name: "B", employee: "HR-EMP-00070", attendance_date: "2026-09-04" },
	]);
	punches();
	assert.deepStrictEqual(routes, []);
	assert.match(messages[0], /one person on one day/);
});

test("the list keeps Mark Attendance", () => {
	assert.ok(controls().labels.includes("Mark Attendance"));
});

test("the employee rides along, or the row cannot name its own day", () => {
	assert.ok(SETTINGS.add_fields.includes("employee"));
});
