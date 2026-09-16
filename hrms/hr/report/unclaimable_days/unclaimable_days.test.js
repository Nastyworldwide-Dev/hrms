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
	"utf8"
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
		/STATUS_FIXABLE, STATUS_ON_PURPOSE, STATUS_NEEDS_HR = "([^"]+)", "([^"]+)", "([^"]+)"/
	);
	assert.ok(statuses, "expected the three status constants");
	const offered = options("status");
	assert.deepStrictEqual(offered, statuses.slice(1, 4));
	// and each has a colour in the formatter, so HR can scan the page
	for (const status of statuses.slice(1, 4)) {
		assert.ok(JS.includes(`"${status}"`) || JS.includes(`${status}:`), `no colour for ${status}`);
	}
});

test("the window starts where recovery starts and ends yesterday", () => {
	const floor = REC.match(/^REPAIR_FLOOR = date\((\d+), (\d+), (\d+)\)/m);
	const iso = `${floor[1]}-${floor[2].padStart(2, "0")}-${floor[3].padStart(2, "0")}`;
	assert.ok(JS.includes(`default: "${iso}"`), `from_date default should be ${iso}`);
	assert.ok(JS.includes("frappe.datetime.add_days(frappe.datetime.get_today(), -1)"));
});

// The report itself still writes nothing and still asks the server nothing of
// its own. Its ONE button is an entry point: it hands the ticked employee-day
// to the Fix Day screen, which owns every correction and every guard.
test("the page computes nothing itself: no call, no confirm", () => {
	assert.ok(!JS.includes("frappe.call"), "the report makes no server call of its own");
	assert.ok(!JS.includes("frappe.confirm"));
});

test("its only button is the Fix entry point into the Fix Day screen", () => {
	const buttons = [...JS.matchAll(/add_inner_button\(__\("([^"]+)"\)/g)].map((m) => m[1]);
	assert.deepStrictEqual(buttons, ["Fix"]);
	assert.ok(JS.includes('frappe.require("fix_day.bundle.js"'), "the screen is loaded on demand");
	assert.ok(JS.includes("hrms.fix_day.open("), "the screen is opened for the ticked row");
	// and only HR sees it
	assert.ok(JS.includes("if (ud_hr()) report.page.add_inner_button"));
});

test("the Fix entry point never sends hours or overtime", () => {
	assert.ok(!JS.includes("working_hours"));
	assert.ok(!JS.includes("ot_hours"));
});
