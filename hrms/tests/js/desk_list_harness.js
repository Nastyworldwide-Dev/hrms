// Loads Desk scripts the way Desk loads them, and watches what a list's onload
// actually registers.
//
// Why this exists (17 Sep 2026): the Fix Day bundle added its "Fix day" button
// to the Employee Checkin list by REASSIGNING frappe.listview_settings for that
// doctype at boot. The doctype's own list script assigns the same key again
// when the list opens — later — so the button was thrown away and HR, standing
// on the page, could not find it. Every test at the time read source text, and
// source text was fine. Order is the thing that was wrong, so the harness runs
// the files in order in one sandbox and asks the result what it registered.
const fs = require("node:fs");
const vm = require("node:vm");

function provide(root) {
	return (namespace) =>
		String(namespace)
			.split(".")
			.reduce((parent, part) => (parent[part] = parent[part] || {}), root);
}

// A page that records every control a script hangs on it.
function fakePage() {
	return {
		actions: [],
		buttons: [],
		add_action_item(label, handler) {
			this.actions.push({ label, handler });
		},
		add_inner_button(label, handler, group) {
			this.buttons.push({ label, handler, group });
		},
	};
}

function fakeListview(checked = []) {
	const page = fakePage();
	return {
		page,
		refresh: () => {},
		get_checked_items: (names_only) => (names_only ? checked.map((row) => row.name) : checked),
	};
}

// `files` in load order, earliest (boot) first.
function loadDesk(files, options = {}) {
	const settings = {};
	const window = {};
	const sandbox = {
		window,
		console: { info: () => {}, warn: () => {}, error: () => {} },
		frappe: {
			listview_settings: settings,
			provide: null,
			call: () => Promise.resolve({ message: null }),
			db: { get_list: () => Promise.resolve([]) },
			msgprint: (message) => (sandbox.__messages.push(message), message),
			utils: { escape_html: (value) => String(value == null ? "" : value) },
			perm: { has_perm: () => options.has_perm !== false },
			// Records WHICH role was asked about: a stub that answers the same for
			// every string cannot tell a correct role list from a typo'd one.
			user: {
				has_role: (role) => {
					sandbox.__roles_checked.push(role);
					return options.has_role !== false;
				},
			},
			ui: { Dialog: function () {}, form: {} },
			datetime: { get_today: () => "2026-09-10", obj_to_str: () => "2026-09-01" },
			model: {},
			views: {},
		},
		__: (text, args) => (args || []).reduce((out, a, i) => out.split(`{${i}}`).join(a), text),
		moment: Object.assign(
			() => ({
				startOf: () => ({ subtract: () => ({}) }),
				toDate: () => new Date("2026-09-10T00:00:00"),
				format: () => "10-09-2026",
			}),
			{}
		),
		format_number: (value) => String(value),
	};
	sandbox.__messages = [];
	sandbox.__roles_checked = [];
	sandbox.frappe.provide = provide(sandbox);
	sandbox.hrms = {};
	for (const file of files) {
		vm.runInNewContext(fs.readFileSync(file, "utf8"), sandbox);
	}
	return { settings, sandbox, messages: sandbox.__messages, roles: sandbox.__roles_checked };
}

module.exports = { loadDesk, fakeListview, fakePage };
