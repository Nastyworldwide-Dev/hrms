// The check-in list answers one question at a glance: did this punch count,
// and under which shift? Run: node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const SOURCE = fs.readFileSync(path.join(__dirname, "employee_checkin_list.js"), "utf8");
const HEAD = SOURCE.split("get_indicator")[0];

test("every state a punch can be in has an indicator", () => {
	for (const state of [
		"Off-Shift",
		"Rejected",
		"Skipped",
		"Awaiting approval",
		"Counted",
		"Not counted yet",
	]) {
		assert.ok(SOURCE.includes(state), `missing indicator: ${state}`);
	}
});

test("the fields behind the indicator are fetched", () => {
	// the list only loads what it shows or is told to add
	for (const field of [
		"skip_auto_attendance",
		"attendance",
		"shift",
		"remote_approval_status",
	]) {
		assert.ok(HEAD.includes(`"${field}"`), `add_fields missing: ${field}`);
	}
});

test("each indicator carries the filter that isolates it", () => {
	assert.ok(SOURCE.includes('"attendance,is,set"'));
	assert.ok(SOURCE.includes('"attendance,is,not set"'));
	assert.ok(SOURCE.includes('"skip_auto_attendance,=,1"'));
});
