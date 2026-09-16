// The page's filters must match the classifier's own labels, start where the
// report module starts, and never offer an action that writes.
// Run: node --test hrms/hr/report/attendance_ownership_check/attendance_ownership_check.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const JS = fs.readFileSync(path.join(__dirname, "attendance_ownership_check.js"), "utf8");
const PY = fs.readFileSync(path.join(__dirname, "attendance_ownership_check.py"), "utf8");
const OWNERSHIP = fs.readFileSync(
	path.join(__dirname, "..", "..", "..", "utils", "attendance_ownership.py"),
	"utf8"
);

function owners() {
	return [...OWNERSHIP.matchAll(/^OWNER_[A-Z]+ = "([a-z]+)"$/gm)].map((m) => m[1]);
}

function options(fieldname) {
	const open = JS.indexOf("options: [", JS.indexOf(`fieldname: "${fieldname}"`));
	return [...JS.slice(open, JS.indexOf("]", open)).matchAll(/"([^"]*)"/g)]
		.map((m) => m[1])
		.filter(Boolean);
}

test("the owner filter offers every label the classifier can return", () => {
	const labels = owners();
	assert.ok(labels.length === 4, `expected four owners, found ${labels}`);
	assert.deepStrictEqual(options("owner"), labels);
});

test("the four filters HR needs are all there, and the window is required", () => {
	for (const field of ["from_date", "to_date", "employee", "owner"]) {
		assert.ok(JS.includes(`fieldname: "${field}"`), `missing filter ${field}`);
	}
	assert.match(JS, /fieldname: "from_date"[\s\S]{0,200}reqd: 1/);
	assert.match(JS, /fieldname: "to_date"[\s\S]{0,200}reqd: 1/);
});

test("the page starts on the date the report module starts on", () => {
	const floor = PY.match(/START_FLOOR = date\((\d+), (\d+), (\d+)\)/);
	assert.ok(floor, "expected START_FLOOR in the report module");
	const [, y, m, d] = floor;
	const iso = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
	assert.ok(JS.includes(`default: "${iso}"`), `expected the from_date default to be ${iso}`);
});

test("today is never the default end of the window", () => {
	assert.match(JS, /add_days\(frappe\.datetime\.get_today\(\), -1\)/);
});

test("the page offers nothing that writes", () => {
	for (const writer of ["frappe.call", "frappe.xcall", "add_custom_button", "set_value"]) {
		assert.ok(!JS.includes(writer), `the report page must stay read-only, found ${writer}`);
	}
});
