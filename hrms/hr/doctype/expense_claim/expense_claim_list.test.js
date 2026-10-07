// Expense Claim has two parts, the decision (approval_status) and the money (status). Desk says what Nadi
// says: Waiting / Approved · unpaid / Paid / Rejected / Cancelled (owner, 5 Oct 2026).
// Run: node --test hrms/hr/doctype/expense_claim/expense_claim_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load() {
	const settings = {};
	const sandbox = { __: (t) => t, frappe: { listview_settings: settings } };
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "expense_claim_list.js"), "utf8"), sandbox);
	return settings["Expense Claim"];
}
const word = (doc) => [...load().get_indicator(doc)];

test("a claim nobody has decided says Waiting", () => {
	assert.deepStrictEqual(word({ docstatus: 0, status: "Draft", approval_status: "Draft" }), ["Waiting", "orange", "docstatus,=,0"]);
});

test("approved but not paid says Approved · unpaid, the same words as Nadi", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Unpaid", approval_status: "Approved" }), ["Approved · unpaid", "blue", "approval_status,=,Approved"]);
	// nothing sanctioned: set_status leaves the stored status "Submitted", and the pill must still list it
	assert.deepStrictEqual(word({ docstatus: 1, status: "Submitted", approval_status: "Approved" }), ["Approved · unpaid", "blue", "approval_status,=,Approved"]);
});

test("paid says Paid", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Paid", approval_status: "Approved" }), ["Paid", "green", "status,=,Paid"]);
});

test("rejected says Rejected, and a click filters on the stored decision", () => {
	assert.deepStrictEqual(word({ docstatus: 1, status: "Rejected", approval_status: "Rejected" }), ["Rejected", "red", "approval_status,=,Rejected"]);
});

test("cancelled says Cancelled", () => {
	assert.deepStrictEqual(word({ docstatus: 2, status: "Cancelled", approval_status: "Approved" }), ["Cancelled", "red", "docstatus,=,2"]);
});

test("a decision saved in Desk but never submitted still says Waiting, never Approved", () => {
	assert.strictEqual(word({ docstatus: 0, status: "Draft", approval_status: "Approved" })[0], "Waiting");
});

test("the doctype no longer carries Frappe's own states, which would outrank this rule", () => {
	const json = JSON.parse(fs.readFileSync(path.join(__dirname, "expense_claim.json"), "utf8"));
	assert.deepStrictEqual(json.states, []);
});

// --- Desk says what Nadi says, asked of Nadi's own rule (owner ruling E1a, 7 Oct 2026) ---
// frontend/src/utils/requestStatus.js is an ES module with no imports, so node loads it as it is
// (frontend/package.json is "type": "module") and the words cannot drift in a copied table.
// Rows are the states Expense Claim.set_status can really produce (docstatus, status, approval_status).
// Nadi's API (get_expense_claims) sends no docstatus, so the Nadi side gets none: it works it out
// from `status`, while Desk has the real docstatus. The two feeds must still land on one word.
const { pathToFileURL } = require("node:url");
const NADI = path.join(__dirname, "..", "..", "..", "..", "frontend", "src", "utils", "requestStatus.js");
async function nadi() {
	const quiet = console.info;
	console.info = () => {}; // requestStatus logs a decided draft; not what this test is about
	try {
		return await import(pathToFileURL(NADI).href);
	} finally {
		console.info = quiet;
	}
}
const REAL_ROWS = [
	{ docstatus: 0, status: "Draft", approval_status: "Draft", want: "Waiting" },
	{ docstatus: 0, status: "Draft", approval_status: "Approved", want: "Waiting" },
	{ docstatus: 0, status: "Draft", approval_status: "Rejected", want: "Waiting" },
	{ docstatus: 1, status: "Unpaid", approval_status: "Approved", want: "Approved · unpaid" },
	{ docstatus: 1, status: "Submitted", approval_status: "Approved", want: "Approved · unpaid" },
	{ docstatus: 1, status: "Paid", approval_status: "Approved", want: "Paid" },
	{ docstatus: 1, status: "Rejected", approval_status: "Rejected", want: "Rejected" },
	{ docstatus: 2, status: "Cancelled", approval_status: "Approved", want: "Cancelled" },
	{ docstatus: 2, status: "Cancelled", approval_status: "Rejected", want: "Cancelled" },
	{ docstatus: 2, status: "Cancelled", approval_status: "Draft", want: "Cancelled" },
];

test("every real state: the Desk word is the word Nadi shows for the same claim", async () => {
	const { requestStatus } = await nadi();
	for (const { docstatus, status, approval_status, want } of REAL_ROWS) {
		const row = JSON.stringify({ docstatus, status, approval_status });
		assert.strictEqual(word({ docstatus, status, approval_status })[0], want, `desk ${row}`);
		assert.strictEqual(requestStatus("Expense Claim", { status, approval_status }).label, want, `nadi ${row}`);
	}
});

test("the Desk colour is the colour family of Nadi's chip, apart from Cancelled", async () => {
	const { requestStatus } = await nadi();
	// Nadi chip variant -> the Desk indicator colour that means the same thing
	const FAMILY = { attention: "orange", progress: "blue", success: "green", danger: "red" };
	for (const { docstatus, status, approval_status, want } of REAL_ROWS) {
		if (want === "Cancelled") continue;
		const { variant } = requestStatus("Expense Claim", { status, approval_status });
		assert.strictEqual(word({ docstatus, status, approval_status })[1], FAMILY[variant], want);
	}
	// KNOWN, deliberate: Nadi greys a cancelled request (muted); every Desk request list says red
	// (hrms/public/js/request_status.bundle.js). One Desk rule beats one doctype going its own way.
	assert.strictEqual(word({ docstatus: 2, status: "Cancelled", approval_status: "Approved" })[1], "red");
});
