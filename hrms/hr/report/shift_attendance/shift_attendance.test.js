// The Shift Attendance report is HR's master attendance sheet. These tests load
// the real report script with a fake `frappe` and drive it the way Desk does:
// onload(report), get_datatable_options, the DataTable editor contract
// (initValue / getValue / setValue), toolbar button actions and dialogs.
// Run: node --test hrms/hr/report/shift_attendance/shift_attendance.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SOURCE = fs.readFileSync(path.join(__dirname, "shift_attendance.js"), "utf8");
const BACKEND = fs.readFileSync(
	path.join(__dirname, "..", "..", "..", "api", "attendance_master_edit.py"),
	"utf8"
);
const API = "hrms.api.attendance_master_edit.";

function translate(text, args) {
	return String(text).replace(/\{(\d+)\}/g, (_, i) => (args ? args[i] : ""));
}

function load({ roles = ["HR User"], handlers = {}, checked = [], confirm_answer = true } = {}) {
	const calls = [];
	const messages = [];
	const dialogs = [];
	const confirms = [];
	const routes = [];
	const page = {
		buttons: new Map(),
		indicator: null,
		add_inner_button(label, action, group) {
			this.buttons.set(label, { action, group });
		},
		remove_inner_button(label) {
			this.buttons.delete(label);
		},
		set_indicator(label, color) {
			this.indicator = { label: String(label), color: String(color) };
		},
		clear_indicator() {
			this.indicator = null;
		},
	};
	const report = {
		page,
		datatable: null,
		refreshed: 0,
		checked,
		data: [ROW_A, ROW_B],
		get_checked_items() {
			return this.checked;
		},
		get_filter_values() {
			return {};
		},
		refresh() {
			this.refreshed += 1;
		},
	};
	class Dialog {
		constructor(opts) {
			this.opts = opts;
			dialogs.push(this);
		}
		show() {}
		hide() {}
	}
	const frappe = {
		query_reports: {},
		query_report: report,
		user: { has_role: (role) => roles.includes(role) },
		datetime: { month_start: () => "2026-09-01", month_end: () => "2026-09-30" },
		defaults: { get_user_default: () => "_Test Company" },
		utils: { escape_html: (s) => String(s).replace(/</g, "&lt;") },
		ui: {
			Dialog,
			form: {
				make_control: () => {
					const control = { value: null };
					control.set_value = (v) => (control.value = v);
					control.get_value = () => control.value;
					return control;
				},
			},
		},
		call({ method, args }) {
			// copy out of the vm realm so deepStrictEqual compares values, not prototypes
			calls.push({ method, args: JSON.parse(JSON.stringify(args)) });
			const handler = handlers[method] || (method === API + "get_days" ? days_handler : null);
			return handler ? handler(args) : Promise.resolve({ message: {} });
		},
		msgprint: (m) => messages.push(typeof m === "string" ? m : m.message),
		show_alert: () => {},
		set_route: (...route) => routes.push(JSON.parse(JSON.stringify(route))),
		confirm: (text, yes, no) => {
			confirms.push(text);
			return confirm_answer ? yes() : no && no();
		},
	};
	const quiet = { info() {}, warn() {}, debug() {}, log() {} };
	const context = vm.createContext({ frappe, __: translate, console: quiet, setTimeout, Promise, JSON });
	vm.runInContext(SOURCE, context);
	const settings = frappe.query_reports["Shift Attendance"];
	return { settings, report, page, calls, messages, dialogs, confirms, routes, frappe };
}

// get_day answers with a revision derived from the day, so a payload can be
// checked against the exact revision each row must carry.
function day_handler(args) {
	return Promise.resolve({ message: { revision: `rev-${args.employee}-${args.attendance_date}` } });
}

function save_ok(args) {
	const rows = JSON.parse(args.rows);
	return Promise.resolve({
		message: { rows: rows.map((r, index) => ({ index, ok: true, conflict: false, code: null })), saved: rows.length, refused: 0 },
	});
}

const ROW_A = { employee: "EMP-1", attendance_date: "2026-09-02", status: "Present", shift: "Day", in_time: "08:00:00", out_time: "17:00:00", name: "ATT-1" };
const ROW_B = { employee: "EMP-2", attendance_date: "2026-09-02", status: "Absent", shift: "Day", in_time: "", out_time: "", name: "ATT-2", hr_owned: 1 };

function editor(settings, rowIndex, fieldname, data) {
	const options = settings.get_datatable_options({ columns: [] });
	return options.getEditor(1, rowIndex, data[fieldname], {}, { fieldname, id: fieldname }, [], data);
}

// What Desk does on open: onload, then the first refresh loads rows and their revisions.
async function ready(settings, report) {
	settings.onload(report);
	await settings.after_refresh(report);
}

function flush() {
	return new Promise((resolve) => setImmediate(resolve));
}

function saved_rows(calls) {
	const saves = calls.filter((c) => c.method === API + "save_rows");
	assert.strictEqual(saves.length, 1, "save_rows must be called exactly once");
	return JSON.parse(saves[0].args.rows);
}

test("staff without an HR role get no edit tools", () => {
	const { settings, report, page } = load({ roles: ["Employee"] });
	settings.onload(report);
	assert.strictEqual(page.buttons.size, 0);
	const options = settings.get_datatable_options({ columns: [] });
	assert.ok(!options.checkboxColumn);
	assert.strictEqual(options.getEditor, undefined);
	const html = settings.formatter("Present", 0, { fieldname: "status" }, ROW_B, (v) => v);
	assert.strictEqual(html, "Present", "no HR badge or highlight for staff");
});

for (const role of ["HR User", "HR Manager", "System Manager"]) {
	test(`${role} gets the edit toolbar and a checkbox column`, () => {
		const { settings, report, page } = load({ roles: [role] });
		settings.onload(report);
		for (const label of ["Edit selected", "Remove selected", "Add row", "Add / change shift", "Hand back to system"]) {
			assert.ok(page.buttons.has(label), `missing ${label}`);
			assert.strictEqual(page.buttons.get(label).group, "Edit Attendance");
		}
		const options = settings.get_datatable_options({ columns: [] });
		assert.strictEqual(options.checkboxColumn, true);
		assert.strictEqual(typeof options.getEditor, "function");
	});
}

// Owner, 21 Sep 2026: the Fix Day tools live on the Employee Checkin list only.
// This report links there — "Punches" in the same group — and no longer opens
// the screen itself.
test("Fix day is gone; Punches opens the check-in list on the one ticked day", () => {
	const { settings, report, page, routes, messages } = load({ checked: [ROW_A] });
	settings.onload(report);
	assert.ok(!page.buttons.has("Fix day"));
	assert.strictEqual(page.buttons.get("Punches").group, "Edit Attendance");
	page.buttons.get("Punches").action();
	assert.deepStrictEqual(routes, [
		["List", "Employee Checkin", { employee: "EMP-1", time: ["Between", ["2026-09-02", "2026-09-02"]] }],
	]);
	report.checked = [ROW_A, ROW_B];
	page.buttons.get("Punches").action();
	assert.strictEqual(routes.length, 1, "two ticked days route nowhere");
	assert.match(messages[0], /exactly one day/);
});

test("only date, shift, status, in and out are editable", () => {
	const { settings } = load();
	const columns = ["employee", "shift", "attendance_date", "status", "in_time", "out_time", "department", "company", "working_hours"].map(
		(fieldname) => ({ fieldname, id: fieldname, editable: false })
	);
	settings.after_datatable_render({ getColumns: () => columns, bodyScrollable: null });
	const editable = columns.filter((c) => c.editable).map((c) => c.fieldname).sort();
	assert.deepStrictEqual(editable, ["attendance_date", "in_time", "out_time", "shift", "status"]);
	assert.strictEqual(editor(settings, 0, "department", ROW_A), false);
	assert.strictEqual(editor(settings, 0, "employee", ROW_A), false);
});

test("cell edits collect as pending changes and read nothing from the server", async () => {
	const { settings, report, page, calls } = load({ handlers: { [API + "get_day"]: day_handler } });
	settings.onload(report);
	const status = editor(settings, 0, "status", ROW_A);
	status.initValue(ROW_A.status);
	assert.strictEqual(status.getValue(), "Present");
	status.setValue("Absent");
	editor(settings, 0, "in_time", ROW_A).setValue("09:05:00");
	await flush();

	assert.strictEqual(calls.length, 0, "the revision was read with the report data");
	assert.deepStrictEqual(page.indicator, { label: "1 unsaved changes", color: "orange" });
	assert.ok(page.buttons.has("Save") && page.buttons.has("Discard"));

	const html = settings.formatter("Present", 0, { fieldname: "status" }, ROW_A, (v) => v);
	assert.match(html, /Absent/, "the cell shows the pending value");
	assert.match(html, /--bg-yellow/, "the pending row is highlighted");

	// putting both values back leaves nothing to save
	editor(settings, 0, "status", ROW_A).setValue("Present");
	editor(settings, 0, "in_time", ROW_A).setValue("08:00");
	assert.strictEqual(page.indicator, null);
	assert.ok(!page.buttons.has("Save"));
});

test("a formatted datetime cell edits as its time", () => {
	const { settings } = load();
	const row = Object.assign({}, ROW_A, { out_time: "03-09-2026 02:15:00" });
	const out = editor(settings, 0, "out_time", row);
	out.initValue(row.out_time);
	assert.strictEqual(out.getValue(), "02:15:00");
});

test("Save sends every pending day in one save_rows call and refreshes", async () => {
	const { settings, report, page, calls } = load({
		handlers: { [API + "get_day"]: day_handler, [API + "save_rows"]: save_ok },
	});
	await ready(settings, report);
	editor(settings, 0, "status", ROW_A).setValue("Half Day");
	editor(settings, 0, "out_time", ROW_A).setValue("13:00");
	editor(settings, 1, "shift", ROW_B).setValue("Night");
	editor(settings, 1, "attendance_date", ROW_B).setValue("2026-09-03");
	await page.buttons.get("Save").action();

	assert.deepStrictEqual(saved_rows(calls), [
		{ employee: "EMP-1", attendance_date: "2026-09-02", action: "edit", changes: { status: "Half Day", out_time: "13:00:00" }, revision: "rev-EMP-1-2026-09-02" },
		{ employee: "EMP-2", attendance_date: "2026-09-02", action: "edit", changes: { shift: "Night", attendance_date: "2026-09-03" }, revision: "rev-EMP-2-2026-09-02" },
	]);
	assert.strictEqual(page.indicator, null, "saved rows are no longer pending");
	assert.strictEqual(report.refreshed, 1);
});

test("a conflict row is reloaded, turns amber and shows the current values", async () => {
	const current = { revision: "rev-new", attendance: [{ docstatus: 1, status: "Absent", shift: "Night", in_time: "", out_time: "" }] };
	const { settings, report, page, calls, messages } = load({
		handlers: {
			[API + "get_day"]: day_handler,
			[API + "save_rows"]: () =>
				Promise.resolve({
					message: {
						rows: [
							{ index: 0, ok: false, conflict: true, code: "conflict", error: "changed", current },
							{ index: 1, ok: false, conflict: false, code: "financial_lock", error: "Salary Slip SAL-1 already depends on this day." },
						],
					},
				}),
		},
	});
	await ready(settings, report);
	editor(settings, 0, "status", ROW_A).setValue("Half Day");
	editor(settings, 1, "status", ROW_B).setValue("Present");
	await page.buttons.get("Save").action();
	assert.strictEqual(calls.filter((c) => c.method === API + "save_rows").length, 1);

	const conflictCell = settings.formatter("Present", 0, { fieldname: "status" }, ROW_A, (v) => v);
	assert.match(conflictCell, /--bg-orange/);
	assert.match(conflictCell, /Changed by someone else — reloaded/);
	assert.doesNotMatch(conflictCell, /Half Day/, "the conflicting edit is not kept to overwrite later");

	const lockedCell = settings.formatter("Absent", 1, { fieldname: "status" }, ROW_B, (v) => v);
	assert.match(lockedCell, /--bg-red/);
	assert.match(lockedCell, /Present/, "a refused non-conflict edit stays pending, never dropped");
	assert.deepStrictEqual(page.indicator, { label: "1 unsaved changes", color: "orange" });

	assert.strictEqual(messages.length, 1);
	assert.match(messages[0], /Changed by someone else — reloaded/);
	assert.match(messages[0], /Now: Status Absent, Shift Night/);
	assert.match(messages[0], /Your change: Status Half Day/);
	assert.match(messages[0], /Payroll or a claim already uses this day/);
	assert.match(messages[0], /Salary Slip SAL-1/);
	assert.strictEqual(report.refreshed, 1);
});

test("Edit selected sends one row per checked day, folding in pending edits", async () => {
	const checked = [ROW_A, Object.assign({}, ROW_A, { name: "ATT-1b" }), ROW_B];
	const { settings, report, page, calls, dialogs } = load({
		checked,
		handlers: { [API + "get_day"]: day_handler, [API + "save_rows"]: save_ok },
	});
	await ready(settings, report);
	editor(settings, 0, "shift", ROW_A).setValue("Night");
	page.buttons.get("Edit selected").action();
	await dialogs[0].opts.primary_action({ status: "Half Day", in_time: "09:00:00", shift: "", out_time: "" });
	assert.deepStrictEqual(saved_rows(calls), [
		{ employee: "EMP-1", attendance_date: "2026-09-02", action: "edit", changes: { shift: "Night", status: "Half Day", in_time: "09:00:00" }, revision: "rev-EMP-1-2026-09-02" },
		{ employee: "EMP-2", attendance_date: "2026-09-02", action: "edit", changes: { status: "Half Day", in_time: "09:00:00" }, revision: "rev-EMP-2-2026-09-02" },
	]);
});

test("Remove selected confirms, then sends action remove", async () => {
	const { settings, report, page, calls, confirms } = load({
		checked: [ROW_A],
		handlers: { [API + "get_day"]: day_handler, [API + "save_rows"]: save_ok },
	});
	await ready(settings, report);
	await page.buttons.get("Remove selected").action();
	assert.strictEqual(confirms.length, 1);
	assert.deepStrictEqual(saved_rows(calls), [
		{ employee: "EMP-1", attendance_date: "2026-09-02", action: "remove", changes: {}, revision: "rev-EMP-1-2026-09-02" },
	]);
});

test("Add / change shift sends only the shift for checked days", async () => {
	const { settings, report, page, calls, dialogs } = load({
		checked: [ROW_B],
		handlers: { [API + "get_day"]: day_handler, [API + "save_rows"]: save_ok },
	});
	await ready(settings, report);
	page.buttons.get("Add / change shift").action();
	await dialogs[0].opts.primary_action({ shift: "Night" });
	assert.deepStrictEqual(saved_rows(calls), [
		{ employee: "EMP-2", attendance_date: "2026-09-02", action: "edit", changes: { shift: "Night" }, revision: "rev-EMP-2-2026-09-02" },
	]);
});

test("Add row reads the day's revision and sends action add", async () => {
	const { settings, report, page, calls, dialogs } = load({
		handlers: { [API + "get_day"]: day_handler, [API + "save_rows"]: save_ok },
	});
	await ready(settings, report);
	page.buttons.get("Add row").action();
	await dialogs[0].opts.primary_action({
		employee: "EMP-9",
		attendance_date: "2026-09-05",
		shift: "Day",
		in_time: "08:00:00",
		out_time: "16:00:00",
		status: "Present",
	});
	assert.deepStrictEqual(calls.find((c) => c.method === API + "get_day").args, { employee: "EMP-9", attendance_date: "2026-09-05" });
	assert.deepStrictEqual(saved_rows(calls), [
		{ employee: "EMP-9", attendance_date: "2026-09-05", action: "add", changes: { status: "Present", shift: "Day", in_time: "08:00:00", out_time: "16:00:00" }, revision: "rev-EMP-9-2026-09-05" },
	]);
});

test("a day whose revision cannot be read is not sent and is reported", async () => {
	const { settings, report, page, calls, messages } = load({
		handlers: {
			[API + "get_days"]: (args) =>
				days_handler(args).then((r) => {
					r.message.days["EMP-2|2026-09-02"] = { revision: null, code: "fenced", error: "not permitted" };
					return r;
				}),
			[API + "save_rows"]: save_ok,
		},
	});
	await ready(settings, report);
	editor(settings, 0, "status", ROW_A).setValue("Absent");
	editor(settings, 1, "status", ROW_B).setValue("Present");
	await page.buttons.get("Save").action();
	assert.deepStrictEqual(saved_rows(calls).map((r) => r.employee), ["EMP-1"]);
	assert.match(messages[0], /EMP-2.*Could not load this day/);
	assert.deepStrictEqual(page.indicator, { label: "1 unsaved changes", color: "orange" });
});

test("Hand back calls hand_back only for HR-edited rows", async () => {
	const { settings, report, page, calls, messages } = load({
		checked: [ROW_A, ROW_B],
		handlers: {
			[API + "get_day"]: day_handler,
			[API + "hand_back"]: () => Promise.resolve({ message: { ok: true, cancelled: "ATT-2" } }),
		},
	});
	await ready(settings, report);
	await page.buttons.get("Hand back to system").action();
	const backs = calls.filter((c) => c.method === API + "hand_back");
	assert.deepStrictEqual(backs.map((c) => c.args), [
		{ employee: "EMP-2", attendance_date: "2026-09-02", revision: "rev-EMP-2-2026-09-02" },
	]);
	assert.strictEqual(calls.filter((c) => c.method === API + "save_rows").length, 0);
	assert.match(messages[0], /EMP-1.*Not edited by HR/);
	assert.strictEqual(report.refreshed, 1);
});

test("HR-edited rows carry a small HR marker in the status cell", () => {
	const { settings } = load();
	const html = settings.formatter("Absent", 1, { fieldname: "status" }, ROW_B, (v) => v);
	assert.match(html, /indicator-pill blue/);
	assert.doesNotMatch(settings.formatter("Present", 0, { fieldname: "status" }, ROW_A, (v) => v), /indicator-pill/);
});

test("every refusal code the backend can return has its own short message", () => {
	const { settings } = load();
	const { sa_code_message, SA_CODE_TEXT } = settings.__grid;
	const codes = new Set([...BACKEND.matchAll(/RowRefused\(\s*"([a-z_]+)"/g)].map((m) => m[1]));
	codes.add("error");
	assert.ok(codes.size >= 14, `expected the backend's codes, found ${[...codes]}`);
	for (const code of codes) {
		assert.ok(SA_CODE_TEXT[code], `no message for ${code}`);
		assert.notStrictEqual(sa_code_message(code), sa_code_message("__unknown__"));
	}
	assert.strictEqual(sa_code_message("conflict"), "Changed by someone else — reloaded");
});

// --- W4: revisions are read when the report data loads, not at click or save ---

function days_handler(args) {
	const days = {};
	JSON.parse(args.employee_dates).forEach((d) => {
		days[`${d.employee}|${d.attendance_date}`] = { revision: `rev-${d.employee}-${d.attendance_date}` };
	});
	return Promise.resolve({ message: { days } });
}

test("revisions load with the report data in one get_days call per 500 days", async () => {
	const { settings, report, calls } = load({ handlers: { [API + "get_days"]: days_handler } });
	settings.onload(report);
	report.data = Array.from({ length: 1001 }, (_, i) => ({ employee: `EMP-${i}`, attendance_date: "2026-09-02" }));
	report.data.push(Object.assign({}, report.data[0])); // a day listed twice is read once
	await settings.after_refresh(report);
	const reads = calls.filter((c) => c.method === API + "get_days");
	assert.deepStrictEqual(reads.map((c) => JSON.parse(c.args.employee_dates).length), [500, 500, 1]);
	editor(settings, 0, "status", ROW_A).setValue("Absent");
	await flush();
	assert.strictEqual(calls.filter((c) => c.method === API + "get_day").length, 0, "a click reads nothing");
});

test("a save carries the revision read when the data loaded, never a fresh one", async () => {
	let version = "loaded";
	const { settings, report, page, calls } = load({
		handlers: {
			[API + "get_days"]: days_handler,
			[API + "get_day"]: () => Promise.resolve({ message: { revision: `rev-${version}` } }),
			[API + "save_rows"]: save_ok,
		},
	});
	settings.onload(report);
	report.data = [ROW_A];
	await settings.after_refresh(report);
	version = "changed-meanwhile";
	editor(settings, 0, "status", ROW_A).setValue("Absent");
	await page.buttons.get("Save").action();
	assert.deepStrictEqual(saved_rows(calls).map((r) => r.revision), ["rev-EMP-1-2026-09-02"]);
	assert.strictEqual(calls.filter((c) => c.method === API + "get_day").length, 0);
});

test("a refresh with pending edits asks first, then drops them so off-screen edits are never saved", async () => {
	const { settings, report, page, calls, confirms } = load({
		handlers: { [API + "get_days"]: days_handler, [API + "save_rows"]: save_ok },
	});
	settings.onload(report);
	report.data = [ROW_A];
	await settings.after_refresh(report);
	editor(settings, 0, "status", ROW_A).setValue("Absent");
	await report.refresh(true); // what a filter change does
	assert.strictEqual(confirms.length, 1);
	assert.strictEqual(report.refreshed, 1);
	assert.strictEqual(page.indicator, null);
	assert.ok(!page.buttons.has("Save"));
	assert.strictEqual(calls.filter((c) => c.method === API + "save_rows").length, 0);
	assert.strictEqual(settings.formatter("Present", 0, { fieldname: "status" }, ROW_A, (v) => v), "Present");
});

test("declining the refresh keeps the edits and the rows they belong to", async () => {
	const { settings, report, page, confirms } = load({
		confirm_answer: false,
		handlers: { [API + "get_days"]: days_handler },
	});
	settings.onload(report);
	report.data = [ROW_A];
	await settings.after_refresh(report);
	editor(settings, 0, "status", ROW_A).setValue("Absent");
	await report.refresh(true);
	assert.strictEqual(confirms.length, 1);
	assert.strictEqual(report.refreshed, 0, "the old rows stay on screen");
	assert.deepStrictEqual(page.indicator, { label: "1 unsaved changes", color: "orange" });
});

test("a refresh with nothing pending asks nothing", async () => {
	const { settings, report, confirms } = load({ handlers: { [API + "get_days"]: days_handler } });
	settings.onload(report);
	await report.refresh();
	assert.strictEqual(confirms.length, 0);
	assert.strictEqual(report.refreshed, 1);
});
