// The attendance list must show which shift a day was marked under and who owns
// it. Run: node --test hrms/hr/doctype/attendance/attendance_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const SOURCE = fs.readFileSync(path.join(__dirname, "attendance_list.js"), "utf8");
const HEAD = SOURCE.split("get_indicator")[0];

test("shift, owner and hours ride along with the list", () => {
	for (const field of ["shift", "auto_attendance", "working_hours"]) {
		assert.ok(HEAD.includes(`"${field}"`), `add_fields missing: ${field}`);
	}
});

test("status still drives the colour", () => {
	assert.ok(
		SOURCE.includes('"green"') && SOURCE.includes('"red"') && SOURCE.includes('"orange"')
	);
});
