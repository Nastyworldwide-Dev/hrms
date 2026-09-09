// The audit's filter must offer every verdict the judge can return, or HR
// cannot narrow to the days that need repairing.
// Run: node --test hrms/hr/report/attendance_day_audit/attendance_day_audit.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const JS = fs.readFileSync(path.join(__dirname, "attendance_day_audit.js"), "utf8");
const PY = fs.readFileSync(path.join(__dirname, "attendance_day_audit.py"), "utf8");

test("every verdict the report labels is selectable in the filter", () => {
	const labelled = [...PY.matchAll(/^\t"([a-z-]+)":/gm)].map((m) => m[1]);
	assert.ok(labelled.length > 5, "expected the verdict label map");
	for (const verdict of labelled) {
		assert.ok(JS.includes(`"${verdict}"`), `filter is missing verdict: ${verdict}`);
	}
});

test("the split-shift day is offered", () => {
	assert.ok(JS.includes('"punches-split-across-shifts"'));
	assert.ok(PY.includes("One day's punches under two shifts"));
});

test("the repair button confirms before writing", () => {
	assert.ok(JS.includes("frappe.confirm"));
	assert.ok(JS.includes("dry_run: 1"));
});
