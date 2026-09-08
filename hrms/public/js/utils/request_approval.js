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
// reject — so the server (get_decision_actions) is the real gate; this list only decides
// which forms to wire the refresh handler onto.
hrms.approval.DECIDE_DOCTYPES = [
	"Leave Application",
	"Shift Request",
	"Expense Claim",
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
];

hrms.approval.is_current = function (frm, review) {
	const valid =
		review &&
		frm._hrms_review === review &&
		!frm.is_new() &&
		!frm.is_dirty() &&
		frm.doc.docstatus === 0 &&
		!frappe.model.has_workflow(frm.doctype) &&
		frm.doctype === review.doctype &&
		frm.doc.name === review.name &&
		frm.doc.modified === review.expected_modified;
	if (!valid) console.debug("[approval] stale or edited review ignored");
	return Boolean(valid);
};

hrms.approval.decide = function (frm, status, review = frm._hrms_review) {
	if (
		!hrms.approval.is_current(frm, review) ||
		!review.actions?.includes(status) ||
		frm._hrms_deciding
	)
		return;
	frappe.confirm(__("{0} this {1}?", [__(status), __(review.doctype)]), () => {
		if (
			!hrms.approval.is_current(frm, review) ||
			!review.actions?.includes(status) ||
			frm._hrms_deciding
		)
			return;
		frm._hrms_deciding = true;
		console.debug("[approval] recording reviewed decision", review.doctype);
		frappe.call({
			method:
				status === "Submit" ? "hrms.api.approval.finalize" : "hrms.api.approval.decide",
			args: {
				doctype: review.doctype,
				name: review.name,
				expected_modified: review.expected_modified,
				...(status === "Submit" ? { docstatus: 1 } : { status }),
			},
			freeze: true,
			freeze_message: __("Recording decision…"),
			callback: () => {
				if (!hrms.approval.is_current(frm, review)) return;
				frappe.show_alert({
					message: __(status === "Submit" ? "Submitted" : status),
					indicator: status === "Rejected" ? "orange" : "green",
				});
				frm.reload_doc();
			},
			always: () => {
				frm._hrms_deciding = false;
			},
		});
	});
};

hrms.approval.add_buttons = function (frm) {
	const review = {
		doctype: frm.doctype,
		name: frm.doc.name,
		expected_modified: frm.doc.modified,
	};
	frm._hrms_review = review;
	console.debug("[approval] refreshing decision controls", frm.doctype);
	// Workflow owns its controls. Editing owns Save, even while a response waits.
	if (frappe.model.has_workflow(frm.doctype)) return;
	frm.remove_custom_button(__("Reject"));
	if (!hrms.approval.is_current(frm, review)) return;
	frm.page.clear_primary_action();
	if (!review.expected_modified) return;
	frappe.call({
		method: "hrms.api.approval.get_decision_actions",
		args: { doctype: review.doctype, name: review.name },
		callback: (r) => {
			if (!hrms.approval.is_current(frm, review)) return;
			const capability = r.message;
			if (!Array.isArray(capability?.actions) || !capability.actions.length) return;
			if (capability.modified !== review.expected_modified) {
				frappe.show_alert({
					message: __("This request changed. Reload it before deciding."),
					indicator: "orange",
				});
				return;
			}
			review.actions = capability.actions.filter((action) =>
				["Approved", "Rejected", "Submit"].includes(action)
			);
			if (review.actions.includes("Approved"))
				frm.page.set_primary_action(__("Approve"), () =>
					hrms.approval.decide(frm, "Approved", review)
				);
			if (review.actions.includes("Rejected"))
				frm.add_custom_button(__("Reject"), () =>
					hrms.approval.decide(frm, "Rejected", review)
				);
			if (review.actions.includes("Submit"))
				frm.page.set_primary_action(__("Submit"), () =>
					hrms.approval.decide(frm, "Submit", review)
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
