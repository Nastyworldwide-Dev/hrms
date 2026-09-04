// Desk Approve/Reject for the request doctypes that decide-then-submit.
//
// The PWA approves through hrms.api.approval.decide — it sets the decision field
// AND submits in ONE atomic, row-locked call (see approval.py: get_value
// for_update, then doc.submit()). Desk had no equivalent, so an approver pressed
// the raw Submit button and on_submit threw "must be Approved or Rejected before
// it can be submitted" — the status was still Open. This gives Desk the SAME
// decide the PWA uses: no parallel logic, no hardcoded status write, no new race
// (decide keeps its lock, permission gate and validators). The raw Submit that
// leads to the dead end is removed for these types, because it never worked.

frappe.provide("hrms.approval");

// Must match hrms/api/approval.py DECIDE_THEN_SUBMIT exactly. If the two ever
// drift, a doctype either loses its Desk buttons or shows them where decide would
// reject — so the server (can_decide) is the real gate; this list only decides
// which forms to wire the refresh handler onto.
hrms.approval.DECIDE_DOCTYPES = [
	"Leave Application",
	"Shift Request",
	"Expense Claim",
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
];

hrms.approval.decide = function (frm, status) {
	frappe.confirm(__("{0} this {1}?", [__(status), __(frm.doctype)]), () => {
		frappe.call({
			method: "hrms.api.approval.decide",
			args: { doctype: frm.doctype, name: frm.doc.name, status: status },
			freeze: true,
			freeze_message: __("Recording decision…"),
			callback: () => {
				frappe.show_alert({
					message: __(status),
					indicator: status === "Approved" ? "green" : "orange",
				});
				frm.reload_doc();
			},
		});
	});
};

hrms.approval.add_buttons = function (frm) {
	// Only a saved draft awaiting a decision.
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	// Raw Submit never works on these (the decide-first guard), so remove it once
	// the draft is saved. Editing keeps Save; the decision is Approve/Reject below.
	if (!frm.is_dirty()) frm.page.clear_primary_action();
	// The server decides visibility — submit permission OR the routed approver, the
	// exact gate decide enforces — so a shown button never just errors, and a
	// routed manager without a blanket submit role still gets it.
	frappe.call({
		method: "hrms.api.approval.can_decide",
		args: { doctype: frm.doctype, name: frm.doc.name },
		callback: (r) => {
			if (!r.message || frm.doc.docstatus !== 0) return;
			frm.page.set_primary_action(__("Approve"), () =>
				hrms.approval.decide(frm, "Approved"),
			);
			frm.add_custom_button(__("Reject"), () =>
				hrms.approval.decide(frm, "Rejected"),
			);
		},
	});
};

hrms.approval.DECIDE_DOCTYPES.forEach((dt) => {
	frappe.ui.form.on(dt, {
		refresh(frm) {
			hrms.approval.add_buttons(frm);
		},
	});
});
