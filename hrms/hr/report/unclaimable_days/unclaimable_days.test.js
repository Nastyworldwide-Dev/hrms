// The report's filters must offer exactly the families and statuses the Python
// detectors produce, start where recovery starts, and never write.
// Run: node --test hrms/hr/report/unclaimable_days/unclaimable_days.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const JS = fs.readFileSync(path.join(__dirname, "unclaimable_days.js"), "utf8");
const REC = fs.readFileSync(
	path.join(__dirname, "..", "..", "..", "utils", "attendance_recovery.py"),
	"utf8",
);

function options(fieldname) {
	const open = JS.indexOf("options: [", JS.indexOf(`fieldname: "${fieldname}"`));
	const block = JS.slice(open, JS.indexOf("]", open));
	return [...block.matchAll(/"([^"]*)"/g)].map((m) => m[1]).filter(Boolean);
}

test("the family filter offers every detector family and nothing else", () => {
	const families = [...REC.matchAll(/^\t\("(F\d+)", "[a-z_]+", /gm)].map((m) => m[1]);
	assert.ok(families.length >= 7, "expected UNCLAIMABLE_FAMILIES in attendance_recovery.py");
	const offered = options("family");
	assert.deepStrictEqual(offered, families);
});

test("the status filter offers the three outcomes HR reads the counts by", () => {
	const statuses = REC.match(
		/STATUS_FIXABLE, STATUS_ON_PURPOSE, STATUS_NEEDS_HR = "([^"]+)", "([^"]+)", "([^"]+)"/,
	);
	assert.ok(statuses, "expected the three status constants");
	const offered = options("status");
	assert.deepStrictEqual(offered, statuses.slice(1, 4));
	// and each has a colour in the formatter, so HR can scan the page
	for (const status of statuses.slice(1, 4)) {
		assert.ok(
			JS.includes(`"${status}"`) || JS.includes(`${status}:`),
			`no colour for ${status}`,
		);
	}
});

test("the window starts where recovery starts and ends yesterday", () => {
	const floor = REC.match(/^REPAIR_FLOOR = date\((\d+), (\d+), (\d+)\)/m);
	const iso = `${floor[1]}-${floor[2].padStart(2, "0")}-${floor[3].padStart(2, "0")}`;
	assert.ok(JS.includes(`default: "${iso}"`), `from_date default should be ${iso}`);
	assert.ok(JS.includes("frappe.datetime.add_days(frappe.datetime.get_today(), -1)"));
});

// The report itself still writes nothing and still asks the server nothing of
// its own. Its ONE button is a link: it opens the Employee Checkin list on the
// ticked employee-day, the only page that carries the Fix Day tools (owner,
// 21 Sep 2026).
test("the page computes nothing itself: no call, no confirm", () => {
	assert.ok(!JS.includes("frappe.call"), "the report makes no server call of its own");
	assert.ok(!JS.includes("frappe.confirm"));
});

test("its only button is Punches, a link to the check-in list; Fix is gone", () => {
	const buttons = [...JS.matchAll(/add_inner_button\(__\("([^"]+)"\)/g)].map((m) => m[1]);
	assert.deepStrictEqual(buttons, ["Punches"]);
	assert.ok(!JS.includes("fix_day.bundle.js"), "the screen is no longer opened from here");
	assert.ok(!JS.includes("hrms.fix_day"));
	assert.ok(JS.includes('frappe.set_route("List", "Employee Checkin"'));
	// and only HR sees it
	assert.ok(JS.includes("if (ud_hr()) report.page.add_inner_button"));
});

test("Punches routes to the ticked row's employee and date", () => {
	const routes = [];
	const messages = [];
	const sandbox = {
		frappe: {
			query_reports: {},
			user: { has_role: () => true },
			datetime: { get_today: () => "2026-09-10", add_days: () => "2026-09-09" },
			set_route: (...route) => routes.push(JSON.parse(JSON.stringify(route))),
			msgprint: (m) => messages.push(m),
			utils: { escape_html: (s) => String(s) },
		},
		console: { info() {} },
		__: (s) => s,
	};
	require("node:vm").runInNewContext(JS, sandbox);
	const report = {
		page: { buttons: [], add_inner_button: (l, h) => report.page.buttons.push({ l, h }) },
	};
	report.get_checked_items = () => [{ employee: "HR-EMP-00069", date: "2026-09-04" }];
	sandbox.frappe.query_reports["Unclaimable Days"].onload(report);
	report.page.buttons[0].h();
	assert.deepStrictEqual(routes, [
		[
			"List",
			"Employee Checkin",
			{ employee: "HR-EMP-00069", time: ["Between", ["2026-09-04", "2026-09-04"]] },
		],
	]);
	report.get_checked_items = () => [];
	report.page.buttons[0].h();
	assert.strictEqual(routes.length, 1);
	assert.match(messages[0], /exactly one row/);
});

test("the Punches link never sends hours or overtime", () => {
	assert.ok(!JS.includes("working_hours"));
	assert.ok(!JS.includes("ot_hours"));
});
