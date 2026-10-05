// Remote Checkin Request is not submittable: its status field is the whole truth. Desk says
// Waiting / Approved / Rejected, like Nadi. Run: node --test hrms/hr/doctype/remote_checkin_request/remote_checkin_request_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load() {
	const settings = {};
	const sandbox = { __: (text) => text, frappe: { listview_settings: settings } };
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "remote_checkin_request_list.js"), "utf8"), sandbox);
	return settings["Remote Checkin Request"];
}

test("a request nobody has decided says Waiting, and a click filters on the stored word", () => {
	const [label, colour, filter] = load().get_indicator({ status: "Pending" });
	assert.deepStrictEqual([label, colour, filter], ["Waiting", "orange", "status,=,Pending"]);
});

test("a decided request says what was decided", () => {
	const s = load();
	// the indicator array is built inside the vm sandbox, so compare its pieces, not the array itself
	assert.deepStrictEqual([...s.get_indicator({ status: "Approved" })], ["Approved", "green", "status,=,Approved"]);
	assert.deepStrictEqual([...s.get_indicator({ status: "Rejected" })], ["Rejected", "red", "status,=,Rejected"]);
});

test("an empty or unknown status reads as Waiting, never as a decision", () => {
	const s = load();
	assert.strictEqual(s.get_indicator({})[0], "Waiting");
	assert.strictEqual(s.get_indicator({ status: "Something" })[0], "Waiting");
});
