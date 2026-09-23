// Desk Approve/Reject for Compensatory Leave Request — Nabil, 15 Sep 2026:
// "yes add that reject button". Comp leave used to be submit-is-approval, so
// Desk showed only the raw Submit. It now decides through
// hrms.api.approval.decide like Leave Application, and Desk must wire it.
// Run: node --test hrms/public/js/utils/request_approval.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("./request_approval.js", import.meta.url), "utf8");
const DOCTYPE = "Compensatory Leave Request";

function desk() {
	const calls = [],
		wired = new Map(),
		buttons = new Map();
	const frm = {
		doctype: DOCTYPE,
		doc: {
			doctype: DOCTYPE,
			name: "HR-CMP-0001",
			modified: "2026-09-15 10:00:00",
			docstatus: 0,
		},
		is_new: () => false,
		is_dirty: () => false,
		page: {
			clear_primary_action() {
				buttons.delete("primary");
			},
			set_primary_action(label, click) {
				buttons.set("primary", { label, click });
			},
		},
		add_custom_button(label, click) {
			buttons.set(label, { label, click });
		},
		remove_custom_button(label) {
			buttons.delete(label);
		},
	};
	const context = vm.createContext({
		hrms: { approval: {} },
		__: (text) => text,
		console: { debug() {}, info() {} },
		frappe: {
			provide() {},
			model: { has_workflow: () => false },
			ui: { form: { on: (doctype, handlers) => wired.set(doctype, handlers) } },
			call(options) {
				calls.push(options);
			},
			// A rejection asks why (audit P0-10); the stub answers like a person.
			prompt(field, callback) {
				callback({ [field.fieldname]: "Cover is short that week" });
			},
			confirm(text, callback) {
				callback();
			},
			show_alert() {},
		},
	});
	vm.runInContext(source, context);
	return { frm, calls, wired, buttons };
}

test("the comp leave form is wired for Desk decisions", () => {
	const { wired } = desk();
	assert.ok(wired.has(DOCTYPE), "Compensatory Leave Request gets no Approve/Reject in Desk");
});

test("the approver sees Approve and Reject, and Reject sends a rejection", () => {
	const { frm, calls, wired, buttons } = desk();
	wired.get(DOCTYPE).refresh(frm);
	const capability = calls.find((c) => c.method === "hrms.api.approval.get_decision_actions");
	assert.ok(capability, "the form never asks the server what the viewer may do");
	capability.callback({
		message: { actions: ["Approved", "Rejected"], modified: frm.doc.modified },
	});
	assert.equal(buttons.get("primary")?.label, "Approve");
	assert.ok(buttons.has("Reject"), "no Reject button for comp leave");

	buttons.get("Reject").click();
	const decision = calls.find((c) => c.method === "hrms.api.approval.decide");
	assert.equal(decision?.args?.status, "Rejected");
	assert.equal(decision?.args?.doctype, DOCTYPE);
});

// Audit P0-10 (review of da51cd501): approval.decide now refuses a rejection
// without a reason, and Desk's Reject sent none — every Desk Reject would have
// failed. Desk asks "Why not?" (required) and sends the answer.
test("Desk's Reject asks why and sends the reason with the decision", () => {
	const decide = source.slice(source.indexOf("hrms.approval.decide = function"));
	assert.match(decide, /frappe\.prompt\([\s\S]*fieldname: "reason"[\s\S]*reqd: 1/);
	assert.match(decide, /status === "Rejected" \? \{ reason \} : \{\}/);
});
