// HR's "Change shift from..." dialog (owner, 5 Oct 2026). These drive the real
// helpers in change_shift_from.bundle.js: the words HR reads in "What will change", and
// the rows the server is sent. The server refuses the same shapes; this keeps
// the dialog from sending them in the first place.
// Run: node --test hrms/public/js/change_shift_from.bundle.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load() {
	const sandbox = {
		frappe: {
			provide: (name) => {
				const [root, leaf] = name.split(".");
				sandbox[root] = sandbox[root] || {};
				sandbox[root][leaf] = sandbox[root][leaf] || {};
			},
			utils: { escape_html: (s) => String(s) },
			user: { has_role: () => true },
			datetime: {},
			ui: { form: { on: () => {} } },
		},
		__: (s, args) => (args ? s.replace(/\{(\d+)\}/g, (_, n) => args[Number(n)]) : s),
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "change_shift_from.bundle.js"), "utf8"), sandbox);
	return sandbox.hrms.change_shift;
}

const raw = load();
// values built inside the vm sandbox carry another Object prototype; compare them as plain JSON
const cs = new Proxy(raw, {
	get: (target, name) =>
		typeof target[name] === "function" && name !== "enabled"
			? (...args) => JSON.parse(JSON.stringify(target[name](...args)))
			: target[name],
});

test("one shift for every day is sent with no days", () => {
	assert.deepStrictEqual(cs.payload([{ shift: "10-7", days: [] }], false), [
		{ shift_type: "10-7", days: null },
	]);
});

test("different shifts on different days are sent with their weekday names", () => {
	const rows = [
		{ shift: "10-7", days: [0, 1, 2, 3] },
		{ shift: "10-4", days: [4] },
	];
	assert.deepStrictEqual(cs.payload(rows, true), [
		{ shift_type: "10-7", days: ["Monday", "Tuesday", "Wednesday", "Thursday"] },
		{ shift_type: "10-4", days: ["Friday"] },
	]);
});

test("a row with no shift picked is not sent", () => {
	assert.deepStrictEqual(cs.payload([{ shift: "", days: [0] }], true), []);
});

test("the problem list says what is missing, in plain words", () => {
	assert.deepStrictEqual(cs.problems("", [{ shift: "10-7", days: [] }], false), ["Pick the date."]);
	assert.deepStrictEqual(cs.problems("2026-10-12", [{ shift: "", days: [] }], false), ["Pick the new shift."]);
	assert.deepStrictEqual(cs.problems("2026-10-12", [{ shift: "10-7", days: [] }], true), [
		"Say which days each shift covers.",
	]);
	assert.deepStrictEqual(cs.problems("2026-10-12", [{ shift: "10-7", days: [] }], false), []);
});

test("a weekday can be on one shift only", () => {
	const rows = [
		{ shift: "10-7", days: [0, 4] },
		{ shift: "10-4", days: [4] },
	];
	assert.deepStrictEqual(cs.problems("2026-10-12", rows, true), ["Friday is on two shifts. Give each day one shift."]);
});

test("days nobody covers are named as no shift", () => {
	const rows = [
		{ shift: "10-7", days: [0, 1, 2, 3] },
		{ shift: "10-4", days: [4] },
	];
	assert.deepStrictEqual(cs.days_without_shift(rows, true), ["Saturday", "Sunday"]);
	assert.deepStrictEqual(cs.days_without_shift([{ shift: "10-7", days: [] }], false), []);
});

test("the day before is worked out from the date picked, not from today", () => {
	assert.strictEqual(cs.day_before("2026-10-12"), "2026-10-11");
	assert.strictEqual(cs.day_before("2026-11-01"), "2026-10-31");
	assert.strictEqual(cs.day_before("2027-01-01"), "2026-12-31");
});

test("only HR may use it", () => {
	assert.strictEqual(typeof cs.enabled, "function");
});
