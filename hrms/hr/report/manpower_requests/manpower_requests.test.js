// The report's filter lists must be exactly the doctype's own Select options, and the report must write
// nothing. Run: node --test hrms/hr/report/manpower_requests/manpower_requests.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const JS = fs.readFileSync(path.join(__dirname, "manpower_requests.js"), "utf8");
const DOCTYPE = JSON.parse(
	fs.readFileSync(
		path.join(__dirname, "..", "..", "doctype", "manpower_request", "manpower_request.json"),
		"utf8",
	),
);

function offered(fieldname) {
	const open = JS.indexOf("options: [", JS.indexOf(`fieldname: "${fieldname}"`));
	const block = JS.slice(open, JS.indexOf("]", open));
	return [...block.matchAll(/"([^"]*)"/g)].map((m) => m[1]);
}

for (const field of ["status", "hiring_status", "urgency"]) {
	test(`the ${field} filter offers every option of the doctype's field and nothing else`, () => {
		const options = DOCTYPE.fields.find((f) => f.fieldname === field).options.split("\n");
		assert.deepStrictEqual(offered(field), ["", ...options.filter(Boolean)]);
	});
}

test("the filters are From/To, Company, Department, Status, Hiring Status, Urgency", () => {
	const names = [...JS.matchAll(/fieldname: "([a-z_]+)"/g)].map((m) => m[1]);
	assert.deepStrictEqual(names, [
		"from_date",
		"to_date",
		"company",
		"department",
		"status",
		"hiring_status",
		"urgency",
	]);
});

test("it never writes", () => {
	assert.doesNotMatch(JS, /frappe\.call|frappe\.db\.set|\.save\(|set_value|insert/);
});
