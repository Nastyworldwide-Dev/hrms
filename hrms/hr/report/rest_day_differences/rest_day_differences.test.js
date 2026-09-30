// The report's filters must match what the Python reads, and default to the
// view HR opens it for: only the people whose rest days would change.
// Run: node --test hrms/hr/report/rest_day_differences/rest_day_differences.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const JS = fs.readFileSync(path.join(__dirname, "rest_day_differences.js"), "utf8");
const PY = fs.readFileSync(path.join(__dirname, "rest_day_differences.py"), "utf8");

function filter(fieldname) {
	const at = JS.indexOf(`fieldname: "${fieldname}"`);
	assert.ok(at !== -1, `${fieldname} filter missing`);
	return JS.slice(at, JS.indexOf("}", at));
}

test("every filter the Python reads is offered", () => {
	for (const name of ["company", "weeks", "only_changed"]) {
		filter(name);
		assert.match(PY, new RegExp(`filters\\.get\\("${name}"`), `${name} is read by the report`);
	}
});

test("weeks defaults to the Python default", () => {
	const def = PY.match(/DEFAULT_WEEKS = (\d+)/)[1];
	assert.match(filter("weeks"), new RegExp(`default: ${def}\\b`));
});

test("it opens on the people whose rest days change", () => {
	assert.match(filter("only_changed"), /default: 1/);
});
