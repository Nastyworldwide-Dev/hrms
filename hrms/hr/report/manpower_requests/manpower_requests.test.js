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
		"utf8"
	)
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

test("status, hiring status and urgency show as coloured pills with their word, as the mockup draws them", () => {
	// design review of the report slice: the mockup (tab 7) draws these three as pills; colour never alone
	for (const field of ["status", "hiring_status", "urgency"]) {
		assert.match(JS, new RegExp(`PILL_FIELDS[^\\n]*"${field}"`), field);
	}
	assert.match(JS, /indicator-pill/);
});

test("the over-30-days flag uses the same rule as the Nadi board (blank hiring status still waits on HR)", () => {
	// run the real formatter: approved and not yet picked up by HR = waiting on HR (board_group)
	const frappe = {
		query_reports: {},
		utils: { escape_html: (t) => t },
		datetime: { get_today: () => "2026-10-22", add_months: (d) => d },
		defaults: { get_user_default: () => "" },
	};
	new Function("frappe", "__", JS)(frappe, (t) => t);
	const { formatter } = frappe.query_reports["Manpower Requests"];
	const days = (data) => formatter("42", null, { fieldname: "days_open" }, data, (v) => v);
	assert.match(days({ status: "Approved", hiring_status: "", days_open: 42 }), /▲/);
	assert.match(
		days({ status: "Approved", hiring_status: "Waiting for HR", days_open: 42 }),
		/▲/
	);
	assert.doesNotMatch(
		days({ status: "Approved", hiring_status: "Recruiting", days_open: 42 }),
		/▲/
	);
	assert.doesNotMatch(days({ status: "Open", hiring_status: "", days_open: 42 }), /▲/);
	assert.doesNotMatch(days({ status: "Approved", hiring_status: "", days_open: 30 }), /▲/);
});
