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

test("HR finds Fix day on the Employee Checkin list", () => {
	assert.ok(
		controls().labels.includes("Fix day"),
		"the pairing screen has no other entry point from this page",
	);
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
	assert.ok(!controls({ has_role: false }).labels.includes("Fix day"));
});

// --- Fix days: tick → choose shift → Apply ---------------------------------
// Owner, 21 Sep 2026: one employee, a range of days, one shift for every punch
// in it, IN and OUT alike. Nothing is written until a preview of the SAME
// inputs has been seen, and the reason is required to apply. These drive the
// real dialog through a fake frappe.ui.Dialog that behaves like Desk's:
// defaults become values, set_value fires onchange, the primary button can be
// disabled, the HTML field has a wrapper that records what was painted.
const FD = "hrms.api.attendance_fix_day.";
const TAPS = [
	{
		name: "CK-1",
		employee: "HR-EMP-00069",
		employee_name: "Norazlin",
		shift_start: "2026-09-04 19:00:00",
		time: "2026-09-04 20:02:00",
	},
	{
		name: "CK-2",
		employee: "HR-EMP-00069",
		employee_name: "Norazlin",
		shift_start: null,
		time: "2026-09-06 08:01:00",
	},
];
const PREVIEW = {
	ok: true,
	dry_run: true,
	days: [
		{
			date: "2026-09-04",
			blocked: null,
			taps: [
				{
					name: "CK-1",
					time: "2026-09-04 20:02:00",
					log_type: "IN",
					before: { shift: "7PM-3.30AM" },
					after: { shift: "8AM-6PM" },
					changed: true,
				},
			],
			rows_to_cancel: [{ name: "HR-ATT-1", status: "Present", hours: 7.5, marked_by_hr: 1 }],
			noise: [],
			session: { in: "20:02:00", out: "03:30:00" },
			result: "will rebuild from 20:02:00 to 03:30:00",
			log: null,
		},
		{
			date: "2026-09-05",
			blocked: "Salary Slip SAL-1 already depends on this day.",
			taps: [],
			rows_to_cancel: [],
			noise: [{ name: "CK-9", why: "duplicate within 2 minutes" }],
			session: null,
			result: "refused: payroll",
			log: null,
		},
	],
	totals: { days: 2, rebuilt: 1, open: 0, blocked: 1, restamped: 1, noise: 1, cancelled: 1 },
};
const APPLIED = Object.assign({}, PREVIEW, {
	dry_run: false,
	days: [
		Object.assign({}, PREVIEW.days[0], { result: "Present 7.4 h", log: "LOG-0004" }),
		PREVIEW.days[1],
	],
});

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
		this.handlers[selector] = handler;
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
		for (const df of opts.fields) {
			if (!df.fieldname) continue;
			this.values[df.fieldname] = df.default === undefined ? null : df.default;
			this.fields_dict[df.fieldname] = { df, $wrapper: new FakeWrapper() };
		}
		FakeDialog.opened.push(this);
	}
	show() {}
	hide() {}
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
	preview() {
		return this.opts.secondary_action();
	}
	apply() {
		return this.opts.primary_action(this.values);
	}
	table() {
		return this.fields_dict.days.$wrapper.painted;
	}
}
FakeDialog.opened = [];

function fixDays({ confirm_answer = true } = {}) {
	const { settings, sandbox } = loadDesk([BUNDLE, LIST]);
	const calls = [];
	const confirms = [];
	let refreshed = 0;
	FakeDialog.opened = [];
	sandbox.frappe.ui.Dialog = FakeDialog;
	sandbox.frappe.db.get_list = () => Promise.resolve(TAPS);
	sandbox.frappe.confirm = (text, yes, no) => {
		confirms.push(text);
		return confirm_answer ? yes() : no();
	};
	sandbox.frappe.call = ({ method, args }) => {
		calls.push({ method, args: JSON.parse(JSON.stringify(args)) });
		if (method === FD + "fix_days") {
			return Promise.resolve({ message: args.dry_run ? PREVIEW : APPLIED });
		}
		if (method === FD + "undo_fix") return Promise.resolve({ message: { ok: true } });
		return Promise.resolve({ message: null });
	};
	const listview = fakeListview(TAPS.map((tap) => ({ name: tap.name })));
	listview.refresh = () => (refreshed += 1);
	settings["Employee Checkin"].onload.call(settings["Employee Checkin"], listview);
	const button = listview.page.buttons.find((b) => b.label === "Fix days");
	assert.ok(button, "HR finds Fix days beside Fix day");
	return {
		open: () => button.handler().then(() => FakeDialog.opened[0]),
		calls,
		confirms,
		messages: sandbox.__messages,
		refreshed: () => refreshed,
	};
}

test("ticking two days of one employee opens Fix days on that employee and range", async () => {
	const dialog = await fixDays().open();
	assert.strictEqual(dialog.opts.title, "Fix days");
	assert.strictEqual(dialog.get_value("employee"), "HR-EMP-00069");
	assert.strictEqual(dialog.get_value("employee_name"), "Norazlin");
	assert.strictEqual(
		dialog.get_value("from_date"),
		"2026-09-04",
		"shift_start wins over the tap's own date",
	);
	assert.strictEqual(dialog.get_value("to_date"), "2026-09-06");
	assert.strictEqual(dialog.fields_dict.employee.df.read_only, 1);
	assert.strictEqual(dialog.fields_dict.shift.df.options, "Shift Type");
	assert.strictEqual(dialog.fields_dict.reason.df.reqd, 1);
});

test("Preview asks the server with dry_run=1 and the chosen shift, writing nothing", async () => {
	const { open, calls } = fixDays();
	const dialog = await open();
	dialog.set_value("shift", "8AM-6PM");
	await dialog.preview();
	assert.deepStrictEqual(calls, [
		{
			method: FD + "fix_days",
			args: {
				dry_run: 1,
				employee: "HR-EMP-00069",
				from_date: "2026-09-04",
				to_date: "2026-09-06",
				shift: "8AM-6PM",
			},
		},
	]);
	assert.match(dialog.table(), /nothing written yet/);
});

test("Apply stays disabled until a preview has run, and again after a field changes", async () => {
	const { open, calls, messages } = fixDays();
	const dialog = await open();
	assert.strictEqual(dialog.primary_disabled, true, "no preview yet");
	dialog.set_value("reason", "wrong roster");
	await dialog.apply();
	assert.strictEqual(calls.filter((c) => !c.args.dry_run).length, 0, "nothing written");
	assert.match(messages[messages.length - 1], /Preview first/);

	await dialog.preview();
	assert.strictEqual(dialog.primary_disabled, false, "previewed: Apply is offered");
	dialog.set_value("to_date", "2026-09-07");
	assert.strictEqual(dialog.primary_disabled, true, "the inputs changed: the preview is stale");
	await dialog.apply();
	assert.strictEqual(calls.filter((c) => !c.args.dry_run).length, 0, "stale preview: no write");
});

test("Apply confirms with the totals, sends dry_run=0 with the reason, refreshes the list", async () => {
	const { open, calls, confirms, refreshed } = fixDays();
	const dialog = await open();
	dialog.set_value("shift", "8AM-6PM");
	await dialog.preview();
	dialog.set_value("reason", "night shift was rostered by mistake");
	await dialog.apply();
	assert.deepStrictEqual(confirms, ["Rebuild 1 days, cancel 1 rows?"]);
	assert.deepStrictEqual(calls[1], {
		method: FD + "fix_days",
		args: {
			dry_run: 0,
			reason: "night shift was rostered by mistake",
			employee: "HR-EMP-00069",
			from_date: "2026-09-04",
			to_date: "2026-09-06",
			shift: "8AM-6PM",
		},
	});
	assert.strictEqual(refreshed(), 1);
	assert.strictEqual(
		dialog.primary_disabled,
		true,
		"applied: a second Apply needs a new preview",
	);
});

test("a preview without a reason never applies", async () => {
	const { open, calls, messages } = fixDays();
	const dialog = await open();
	await dialog.preview();
	await dialog.apply();
	assert.strictEqual(calls.length, 1, "only the preview reached the server");
	assert.match(messages[messages.length - 1], /Say why/);
});

test("the table shows each day: restamp, row to cancel, noise, and a blocked day's reason", async () => {
	const dialog = await fixDays().open();
	await dialog.preview();
	const table = dialog.table();
	assert.match(
		table,
		/IN 20:02 7PM-3\.30AM → <b>8AM-6PM<\/b>/,
		"before → after on a changed punch",
	);
	assert.match(table, /Present 7\.5 h \(HR\)/, "the row to cancel, marked HR");
	assert.match(table, /CK-9: duplicate within 2 minutes/, "noise with its reason");
	assert.match(table, /will rebuild from 20:02:00 to 03:30:00/);
	assert.match(
		table,
		/table-warning[^]*indicator-pill orange">Salary Slip SAL-1 already depends on this day\./,
		"the blocked day in the refusal colour with its reason",
	);
	assert.match(
		table,
		/2 days · 1 rebuilt · 0 left open · 1 blocked · 1 punches restamped · 1 noise · 1 rows cancelled/,
	);
	assert.doesNotMatch(table, /Undo/, "nothing to undo before Apply");
});

test("after Apply each rebuilt day offers Undo, which undoes that day's own log", async () => {
	const { open, calls, refreshed } = fixDays();
	const dialog = await open();
	await dialog.preview();
	dialog.set_value("reason", "wrong roster");
	await dialog.apply();
	const table = dialog.table();
	assert.match(table, /Present 7\.4 h/, "actual results replace the preview");
	assert.match(table, /data-fd-undo="LOG-0004"/);
	assert.strictEqual(
		(table.match(/data-fd-undo=/g) || []).length,
		1,
		"a blocked day has no Undo",
	);
	await dialog.fields_dict.days.$wrapper.handlers["[data-fd-undo]"]({
		currentTarget: { getAttribute: () => "LOG-0004" },
	});
	assert.deepStrictEqual(calls[2], { method: FD + "undo_fix", args: { log_entry: "LOG-0004" } });
	assert.strictEqual(refreshed(), 2);
});

test("declining the confirm writes nothing", async () => {
	const { open, calls } = fixDays({ confirm_answer: false });
	const dialog = await open();
	await dialog.preview();
	dialog.set_value("reason", "wrong roster");
	await dialog.apply();
	assert.strictEqual(calls.length, 1);
});

test("a non-HR user is not offered Fix days", () => {
	assert.ok(!controls({ has_role: false }).labels.includes("Fix days"));
});
