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

// --- the entry point HR actually has to find -------------------------------
// Reported 17 Sep 2026, by the owner standing on this page: "im at employee
// checkin page yet i cant see things that is mentioned. how do i even pair the
// the attendance to become one row?" The Fix Day bundle did register a
// "Fix day" button here — at boot — and then this file, which Desk loads when
// the list opens, assigned frappe.listview_settings["Employee Checkin"] again
// and threw it away. Nothing read the source and found it missing, because the
// source was fine. So these load both files in Desk's real order.
const { loadDesk, fakeListview } = require("../../../tests/js/desk_list_harness.js");

const BUNDLE = path.join(__dirname, "..", "..", "..", "public", "js", "fix_day.bundle.js");
const LIST = path.join(__dirname, "employee_checkin_list.js");

function controls(options) {
	const { settings, sandbox, roles } = loadDesk([BUNDLE, LIST], options);
	const listview = fakeListview([]);
	settings["Employee Checkin"].onload.call(settings["Employee Checkin"], listview);
	return {
		labels: listview.page.actions.concat(listview.page.buttons).map((c) => c.label),
		sandbox,
		roles,
	};
}

test("HR finds exactly one Fix attendance button on the Employee Checkin list", () => {
	// Owner, 21 Sep 2026: one button. "Fix day" and "Fix days" are gone.
	const labels = controls().labels;
	assert.strictEqual(labels.filter((l) => l === "Fix attendance").length, 1);
	assert.ok(!labels.includes("Fix day"), "the old single-day door is gone");
	assert.ok(!labels.includes("Fix days"), "the old range form is gone");
});

test("the list keeps its own action when the bundle is loaded first", () => {
	// The regression cut both ways: whichever file assigned last won outright.
	assert.ok(controls().labels.includes("Fetch Shifts"), "Fetch Shifts must survive");
});

test("the gate asks for the HR roles by name", () => {
	// A stub that answers the same for every string cannot tell a correct role
	// list from a typo'd one, and a renamed role would take the button away in
	// production with this suite still green. The names come from the rule —
	// only HR corrects a day — not from the bundle's own constant.
	// Asked with nobody holding any of them: a matching role short-circuits the
	// check, so only a refused user sees the whole list go by.
	const asked = controls({ has_role: false }).roles;
	for (const role of ["HR User", "HR Manager", "System Manager"]) {
		assert.ok(asked.includes(role), `the gate never asked about ${role}`);
	}
});

test("a non-HR user is not offered the fix screen", () => {
	assert.ok(!controls({ has_role: false }).labels.includes("Fix attendance"));
});

// --- Fix attendance: tick the pair → Save & rebuild ----------------------------
// Owner, 21 Sep 2026: keep the compact Fix day dialog. A tick means "this punch
// counts"; the type cell flips; one Shift box applies to the pair; unticked
// punches are deleted (the fix log keeps a copy, Undo brings them back). The
// After line is computed HERE from the ticks, so HR sees the row before it is
// written. These drive the real dialog through a fake frappe.ui.Dialog that
// behaves like Desk's: defaults become values, set_value fires onchange, the
// primary button can be disabled or swapped, the HTML fields have wrappers that
// record what was painted and which handlers were hung on them.
const FD = "hrms.api.attendance_fix_day.";
const EMP = "HR-EMP-00071";

// Norazmi, 27 Aug: four punches, three rows. The engine's pair is 21:00 → 08:07.
function tap(name, time, log_type, extra) {
	return Object.assign(
		{ name, time, log_type, shift: "7PM-3.30AM", state: "counted", counted: false },
		extra || {},
	);
}
const DAY_27 = {
	employee: EMP,
	employee_name: "Norazmi",
	date: "2026-08-27",
	seen_modified: "2026-08-28 09:00:00.000001",
	taps: [
		tap("CK-A", "2026-08-27 08:00:00", "IN", { shift: "8AM-6PM", counted: true }),
		tap("CK-B", "2026-08-27 19:00:00", "OUT", { shift: "8AM-6PM", counted: true }),
		tap("CK-C", "2026-08-27 21:00:00", "IN", { counted: true, suggested: "IN" }),
		tap("CK-D", "2026-08-28 08:07:00", "OUT", { counted: true, suggested: "OUT" }),
		tap("CK-X", "2026-08-27 21:00:30", "IN", { state: "skipped", why: "burst within 45 s" }),
	],
	attendance: [
		{ name: "HR-ATT-1", shift: "8AM-6PM", status: "Present", in_time: "08:00:00", out_time: "19:00:00", hours: 11, overtime: 0 },
		{ name: "HR-ATT-2", shift: "7PM-3.30AM", status: "Present", in_time: "21:00:00", out_time: "08:07:00", hours: 11.1, overtime: 0 },
		{ name: "HR-ATT-3", shift: null, status: "Absent", in_time: null, out_time: null, hours: 0, overtime: 0 },
	],
	blocked: null,
};
// 29 Aug: a plain day whose OUT came from an approved Forgotten check-out.
const DAY_29 = {
	employee: EMP,
	employee_name: "Norazmi",
	date: "2026-08-29",
	seen_modified: "2026-08-29 20:00:00.000000",
	taps: [
		tap("CK-E", "2026-08-29 09:00:00", "IN", { shift: "8AM-6PM", counted: true, suggested: "IN" }),
		tap("CK-F", "2026-08-29 18:00:00", "OUT", {
			shift: "8AM-6PM",
			counted: true, suggested: "OUT",
			linked_request: "Attendance Request HR-ATR-0007",
		}),
	],
	attendance: [],
	blocked: null,
};
const DAYS = { "2026-08-27": DAY_27, "2026-08-29": DAY_29 };
const LIST_ROWS = {
	"CK-A": { name: "CK-A", employee: EMP, shift_start: "2026-08-27 08:00:00", time: "2026-08-27 08:00:00", shift: "8AM-6PM" },
	"CK-D": { name: "CK-D", employee: EMP, shift_start: "2026-08-27 19:00:00", time: "2026-08-28 08:07:00", shift: "7PM-3.30AM" },
	"CK-E": { name: "CK-E", employee: EMP, shift_start: "2026-08-29 08:00:00", time: "2026-08-29 09:00:00", shift: "8AM-6PM" },
	"CK-Z": { name: "CK-Z", employee: "HR-EMP-00002", shift_start: null, time: "2026-08-27 09:00:00", shift: null },
};

class FakeWrapper {
	constructor() {
		this.painted = "";
		this.handlers = {};
	}
	html(markup) {
		this.painted = String(markup);
		return this;
	}
	off() {
		return this;
	}
	on(event, selector, handler) {
		this.handlers[`${event.split(".")[0]} ${selector}`] = handler;
		return this;
	}
	find() {
		return { replaceWith: () => {} };
	}
}

class FakeDialog {
	constructor(opts) {
		this.opts = opts;
		this.values = {};
		this.fields_dict = {};
		this.primary_disabled = false;
		this.primary_label = opts.primary_action_label;
		this.primary = opts.primary_action;
		this.hidden = false;
		for (const df of opts.fields) {
			if (!df.fieldname) continue;
			this.values[df.fieldname] = df.default === undefined ? null : df.default;
			this.fields_dict[df.fieldname] = { df, $wrapper: new FakeWrapper() };
		}
		FakeDialog.opened.push(this);
	}
	show() {}
	hide() {
		this.hidden = true;
	}
	get_value(name) {
		return this.values[name];
	}
	set_value(name, value) {
		this.values[name] = value;
		const df = this.fields_dict[name].df;
		if (df.onchange) df.onchange();
	}
	disable_primary_action() {
		this.primary_disabled = true;
	}
	enable_primary_action() {
		this.primary_disabled = false;
	}
	set_primary_action(label, click) {
		this.primary_label = label;
		this.primary = click;
	}
	// what HR sees
	screen() {
		return this.fields_dict.screen.$wrapper.painted;
	}
	summary() {
		return this.fields_dict.summary.$wrapper.painted;
	}
	// what HR does: the handlers the bundle hung on the screen, fed a fake event
	fire(event, selector, attrs) {
		const handler = this.fields_dict.screen.$wrapper.handlers[`${event} ${selector}`];
		assert.ok(handler, `no ${event} handler for ${selector}`);
		return handler({
			preventDefault() {},
			currentTarget: Object.assign(
				{ getAttribute: (key) => (attrs[key] === undefined ? null : attrs[key]) },
				attrs,
			),
		});
	}
	tick(name, checked) {
		return this.fire("change", "[data-fd-tick]", { "data-fd-tick": name, checked });
	}
	flip(name) {
		return this.fire("click", "[data-fd-flip]", { "data-fd-flip": name });
	}
	act(action) {
		return this.fire("click", "[data-fd-action]", { "data-fd-action": action });
	}
	save() {
		return this.primary(this.values);
	}
}
FakeDialog.opened = [];

function fixAttendance({ ticked = ["CK-A", "CK-D"], prompt_time = "08:07", throw_on_save = null } = {}) {
	const { settings, sandbox } = loadDesk([BUNDLE, LIST]);
	const calls = [];
	let refreshed = 0;
	let logs = 0;
	FakeDialog.opened = [];
	sandbox.frappe.ui.Dialog = FakeDialog;
	sandbox.frappe.db.get_list = (doctype, { filters }) =>
		Promise.resolve(filters.name[1].map((name) => LIST_ROWS[name]));
	sandbox.frappe.prompt = (fields, then) => then({ time: `${prompt_time}:00` });
	sandbox.frappe.confirm = (text, yes) => yes();
	sandbox.frappe.show_alert = () => {};
	sandbox.frappe.call = ({ method, args }) => {
		calls.push({ method, args: JSON.parse(JSON.stringify(args)) });
		if (method === FD + "get_day") {
			return Promise.resolve({ message: JSON.parse(JSON.stringify(DAYS[args.date])) });
		}
		if (method === FD + "save_day") {
			if (throw_on_save) return Promise.reject(new Error(throw_on_save));
			logs += 1;
			return Promise.resolve({
				message: {
					ok: true,
					log: `LOG-${logs}`,
					before: { days: {} },
					after: {
						days: {
							[args.date]: [
								{ name: "HR-ATT-9", shift: "7PM-3.30AM", status: "Present", in_time: "21:00:00", out_time: "08:07:00", hours: 11.1, overtime: 0 },
							],
						},
					},
					rebuild: {},
					warnings: args.date === "2026-08-27" ? ["21:00 is outside 8AM-6PM; the roster says 7PM-3.30AM"] : [],
				},
			});
		}
		if (method === FD + "undo_fix") return Promise.resolve({ message: { ok: true } });
		return Promise.resolve({ message: null });
	};
	const listview = fakeListview(ticked.map((name) => ({ name })));
	listview.refresh = () => (refreshed += 1);
	settings["Employee Checkin"].onload.call(settings["Employee Checkin"], listview);
	const button = listview.page.buttons.find((b) => b.label === "Fix attendance");
	assert.ok(button, "HR finds Fix attendance");
	return {
		open: () => button.handler().then(() => FakeDialog.opened[0]),
		calls,
		messages: sandbox.__messages,
		refreshed: () => refreshed,
	};
}
const saves = (calls) => calls.filter((c) => c.method === FD + "save_day");

test("the dialog opens on the earliest ticked day, pre-ticks the engine's pair, no six buttons", async () => {
	const { open, calls } = fixAttendance();
	const dialog = await open();
	assert.strictEqual(dialog.opts.title, "Fix attendance");
	assert.deepStrictEqual(calls[0], { method: FD + "get_day", args: { employee: EMP, date: "2026-08-27" } });
	const screen = dialog.screen();
	assert.match(screen, /Norazmi/);
	assert.match(screen, /data-fd-tick="CK-C" checked/);
	assert.match(screen, /data-fd-tick="CK-D" checked/);
	// A and B count today but the engine did not suggest them: the suggestion
	// wins over "counted" (it is read per tap, as get_day sends it)
	assert.doesNotMatch(screen, /data-fd-tick="CK-A" checked/);
	assert.doesNotMatch(screen, /data-fd-tick="CK-B" checked/);
	assert.doesNotMatch(screen, /data-fd-tick="CK-A" checked/);
	for (const gone of [
		"Rebuild this day",
		"Pair as one session",
		"Move to shift",
		"Ignore tap",
		"Bring tap back",
		"Add missing tap",
		"remove the duplicate first",
		"HR-ATT-1",
	]) {
		assert.ok(!screen.includes(gone), `${gone} is gone from the screen`);
	}
	assert.strictEqual(dialog.fields_dict.shift.df.options, "Shift Type");
	assert.strictEqual(dialog.get_value("shift"), "7PM-3.30AM", "the ticked IN's shift");
	assert.strictEqual(dialog.fields_dict.reason.df.reqd, 1);
	assert.strictEqual(dialog.primary_label, "Save & rebuild");
});

test("the After line is computed from the ticks; unticking says how many will be deleted", async () => {
	const dialog = await fixAttendance().open();
	assert.match(
		dialog.summary(),
		/After: Present · 21:00 → 08:07 · 11\.1 h · lands on 27 Aug \(7PM-3\.30AM\)/,
	);
	assert.match(dialog.summary(), /2 punches will be deleted/);
	assert.match(dialog.summary(), /Now: Present · 8AM-6PM · 08:00 → 19:00 · 11 h \| Present .* \| Absent/, "today's rows in one line");
	assert.doesNotMatch(dialog.summary(), /HR-ATT-/, "no record ids in what HR reads");
	assert.match(dialog.screen(), /fd-struck[^>]*data-fd-row="CK-A"/, "an unticked row is struck through");
	// HR's ticks win over the suggestion
	dialog.tick("CK-C", false);
	dialog.tick("CK-D", false);
	dialog.tick("CK-A", true);
	dialog.tick("CK-B", true);
	assert.match(
		dialog.summary(),
		/After: Present · 08:00 → 19:00 · 11\.0 h · lands on 27 Aug \(8AM-6PM\)/,
	);
	assert.strictEqual(dialog.get_value("shift"), "8AM-6PM", "the shift follows the ticked IN");
	assert.strictEqual(dialog.primary_disabled, false);
});

test("two ticked pairs are one row with the hours added up", async () => {
	const dialog = await fixAttendance().open();
	dialog.tick("CK-A", true);
	dialog.tick("CK-B", true);
	assert.match(
		dialog.summary(),
		/After: Present · 08:00 → 08:07 · 22\.1 h \(two sessions, added up\) · lands on 27 Aug/,
	);
});

test("G4: not one IN and one OUT per session turns Save off with the reason", async () => {
	const dialog = await fixAttendance().open();
	dialog.flip("CK-D");
	assert.match(dialog.screen(), /data-fd-flip="CK-D"[^>]*>IN</, "the type cell flipped");
	assert.match(dialog.summary(), /Tick 1 IN and 1 OUT for each session \(ticked: 2 IN, 0 OUT\)/);
	assert.doesNotMatch(dialog.summary(), /After:/);
	assert.strictEqual(dialog.primary_disabled, true);
	dialog.flip("CK-D");
	assert.strictEqual(dialog.primary_disabled, false, "flipping back restores Save");
});

test("G6: an IN after an OUT is refused", async () => {
	const dialog = await fixAttendance().open();
	dialog.tick("CK-D", false);
	dialog.tick("CK-B", true);
	assert.match(dialog.summary(), /IN after OUT: 21:00 IN comes after 19:00 OUT/);
	assert.strictEqual(dialog.primary_disabled, true);
});

test("G3: a pair longer than 20 h is refused", async () => {
	const dialog = await fixAttendance().open();
	dialog.tick("CK-C", false);
	dialog.tick("CK-A", true);
	assert.match(dialog.summary(), /this pair is 24\.1 h long/);
	assert.strictEqual(dialog.primary_disabled, true);
});

test("G10: overlapping sessions are refused", async () => {
	const dialog = await fixAttendance().open();
	dialog.tick("CK-A", true);
	dialog.tick("CK-B", true);
	dialog.flip("CK-B");
	dialog.flip("CK-C");
	assert.match(dialog.summary(), /sessions overlap: 19:00 IN opens before 08:00 IN is closed/);
	assert.strictEqual(dialog.primary_disabled, true);
});

test("G5: one tick is saved as open only through Leave open", async () => {
	const { open, calls } = fixAttendance();
	const dialog = await open();
	dialog.tick("CK-D", false);
	assert.match(dialog.summary(), /one punch ticked: add its pair or Leave open/);
	assert.strictEqual(dialog.primary_disabled, true);
	assert.match(dialog.screen(), /data-fd-action="leave_open"/);
	dialog.act("leave_open");
	assert.match(dialog.summary(), /After: no row \(left open\) · 21:00 IN/);
	assert.strictEqual(dialog.primary_disabled, false);
	dialog.set_value("reason", "she never clocked out");
	await dialog.save();
	assert.strictEqual(saves(calls)[0].args.leave_open, 1);
	assert.deepStrictEqual(JSON.parse(saves(calls)[0].args.pairs), [
		{ in: "CK-C", out: null, shift: "7PM-3.30AM" },
	]);
});

test("Save & rebuild sends the ticks as given, once per touched day, then offers Undo", async () => {
	const { open, calls, refreshed } = fixAttendance();
	const dialog = await open();
	await dialog.save();
	assert.strictEqual(saves(calls).length, 0, "no reason: nothing written");
	dialog.set_value("reason", "two rows for one night");
	await dialog.save();
	assert.deepStrictEqual(saves(calls), [
		{
			method: FD + "save_day",
			args: {
				employee: EMP,
				date: "2026-08-27",
				pairs: JSON.stringify([{ in: "CK-C", out: "CK-D", shift: "7PM-3.30AM" }]),
				delete: JSON.stringify(["CK-A", "CK-B"]),
				reason: "two rows for one night",
				leave_open: 0,
				seen_modified: "2026-08-28 09:00:00.000001",
			},
		},
	]);
	assert.match(dialog.summary(), /rebuilt \(LOG-1\)[^]*After: Present · 7PM-3.30AM · 21:00 → 08:07 · 11.1 h/, "the result replaces the After line");
	assert.match(dialog.summary(), /alert-warning[^]*21:00 is outside 8AM-6PM/, "warnings are yellow notes");
	assert.strictEqual(dialog.primary_label, "Undo");
	assert.strictEqual(refreshed(), 1);
	await dialog.save();
	assert.deepStrictEqual(
		calls.filter((c) => c.method === FD + "undo_fix"),
		[{ method: FD + "undo_fix", args: { log_entry: "LOG-1", reason: "two rows for one night" } }],
	);
	assert.strictEqual(calls[calls.length - 1].method, FD + "get_day", "the day is read again");
	assert.strictEqual(dialog.primary_label, "Save & rebuild", "Undo done: Save is back");
	assert.strictEqual(refreshed(), 2);
});

test("+ Add OUT adds a ticked new row and is sent as a time", async () => {
	const { open, calls } = fixAttendance({ prompt_time: "08:07" });
	const dialog = await open();
	dialog.tick("CK-D", false);
	dialog.act("add_out");
	assert.match(dialog.screen(), /new/);
	assert.match(
		dialog.summary(),
		/After: Present · 21:00 → 08:07 · 11\.1 h/,
		"a clock before the IN is the next morning",
	);
	dialog.set_value("reason", "reader missed the out");
	await dialog.save();
	assert.deepStrictEqual(JSON.parse(saves(calls)[0].args.pairs), [
		{ in: "CK-C", out: { time: "08:07" }, shift: "7PM-3.30AM" },
	]);
	assert.deepStrictEqual(JSON.parse(saves(calls)[0].args.delete), ["CK-A", "CK-B", "CK-D"]);
});

test("the Shift box applies to the pair", async () => {
	const { open, calls } = fixAttendance();
	const dialog = await open();
	dialog.set_value("shift", "8AM-6PM");
	assert.match(dialog.summary(), /\(8AM-6PM\)/);
	dialog.set_value("reason", "wrong roster");
	await dialog.save();
	assert.deepStrictEqual(JSON.parse(saves(calls)[0].args.pairs)[0].shift, "8AM-6PM");
});

test("a hidden punch is listed greyed with why; ticking it restores it", async () => {
	const dialog = await fixAttendance().open();
	assert.match(dialog.screen(), /text-muted[^]*CK-X[^]*burst within 45 s/);
	dialog.tick("CK-X", true);
	assert.match(dialog.summary(), /Tick 1 IN and 1 OUT/, "a restored IN takes part in the rule");
});

test("several ticked days: Next day walks them and Save & rebuild counts the visited days", async () => {
	const { open, calls } = fixAttendance({ ticked: ["CK-D", "CK-E"] });
	const dialog = await open();
	assert.match(dialog.screen(), /data-fd-nav="next"/);
	assert.doesNotMatch(dialog.screen(), /data-fd-nav="prev"/);
	assert.strictEqual(dialog.primary_label, "Save & rebuild");
	await dialog.fire("click", "[data-fd-nav]", { "data-fd-nav": "next" });
	assert.strictEqual(calls[1].args.date, "2026-08-29");
	assert.match(dialog.screen(), /2026-08-29/);
	assert.match(dialog.screen(), /data-fd-nav="prev"/);
	assert.strictEqual(dialog.get_value("shift"), "8AM-6PM", "the shift box follows the day");
	assert.strictEqual(dialog.primary_label, "Save & rebuild 2 days");
	dialog.set_value("reason", "night glitch");
	await dialog.save();
	assert.deepStrictEqual(
		saves(calls).map((c) => c.args.date),
		["2026-08-27", "2026-08-29"],
		"one save per visited day, in date order",
	);
	assert.strictEqual(saves(calls)[1].args.delete, "[]");
});

test("a punch from an approved request cannot be unticked", async () => {
	const { open } = fixAttendance({ ticked: ["CK-E"] });
	const dialog = await open();
	assert.match(dialog.screen(), /data-fd-tick="CK-F" checked disabled/);
	assert.match(dialog.screen(), /from approved request/);
	dialog.tick("CK-F", false);
	assert.match(dialog.summary(), /After: Present · 09:00 → 18:00/);
	assert.doesNotMatch(dialog.summary(), /will be deleted/);
});

test("two people's punches are refused", async () => {
	const { open, messages } = fixAttendance({ ticked: ["CK-A", "CK-Z"] });
	await open();
	assert.strictEqual(FakeDialog.opened.length, 0);
	assert.match(messages[messages.length - 1], /Tick taps of one person/);
});

test("a refusal from the server leaves Save on and writes no further day", async () => {
	const { open, calls } = fixAttendance({
		ticked: ["CK-D", "CK-E"],
		throw_on_save: "reopen the day",
	});
	const dialog = await open();
	await dialog.fire("click", "[data-fd-nav]", { "data-fd-nav": "next" });
	dialog.set_value("reason", "x");
	await dialog.save();
	assert.strictEqual(saves(calls).length, 1, "the second day is not attempted");
	assert.strictEqual(dialog.primary_label, "Save & rebuild 2 days");
	assert.strictEqual(dialog.primary_disabled, false);
});

