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

// --- Desk says what Nadi says, asked of Nadi's own rule (owner ruling E1a, 7 Oct 2026) ---
// frontend/src/utils/requestStatus.js is an ES module with no imports, so node loads it as it is
// (frontend/package.json is "type": "module") and the words cannot drift in a copied table.
const { pathToFileURL } = require("node:url");
const NADI = path.join(__dirname, "..", "..", "..", "..", "frontend", "src", "utils", "requestStatus.js");
// Nadi chip variant -> the Desk indicator colour that means the same thing
const FAMILY = { attention: "orange", success: "green", danger: "red" };

test("each stored status: the Desk word and colour are Nadi's for the same request", async () => {
	const { requestStatus } = await import(pathToFileURL(NADI).href);
	const s = load();
	// Pending is the stored word; Nadi and Desk both say Waiting for it
	for (const [status, want] of [["Pending", "Waiting"], ["Approved", "Approved"], ["Rejected", "Rejected"]]) {
		const nadi = requestStatus("Remote Checkin Request", { status });
		const [label, colour] = s.get_indicator({ status });
		assert.strictEqual(nadi.label, want, `nadi ${status}`);
		assert.strictEqual(label, nadi.label, `desk word for ${status}`);
		assert.strictEqual(colour, FAMILY[nadi.variant], `desk colour for ${status}`);
	}
});
