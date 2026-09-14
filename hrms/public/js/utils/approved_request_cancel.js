// Desk Cancel for an approved request — hotfix, 14 Sep 2026.
//
// HR and the request's approver (named, or the employee's reports_to manager) may
// cancel an approved request (hrms/utils/approved_request_guard.py). Desk's own
// Cancel needs the cancel DocPerm, which a reports_to manager holding only
// Employee lacks. So when native Cancel is absent this asks the server
// (hrms.api.approval.can_cancel_approved) and, on yes, adds a Cancel that goes
// through hrms.api.approval.finalize — which elevates the routed cancel and still
// runs the guard. The server re-checks everything; this only decides the button.

frappe.provide("hrms.approved_request_cancel");

// Must match hrms/utils/approved_request_guard.py DECISION_FIELD_BY_DOCTYPE
// (pinned by hrms/api/test_approval.py).
hrms.approved_request_cancel.APPROVED_CANCEL_DOCTYPES = [
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"Attendance Request",
	"OT Request",
	"Replacement Leave Claim",
	"Compensatory Leave Request",
	"Employee Advance",
	"Travel Request",
];

hrms.approved_request_cancel.setup = function (frm) {
	if (frm.doc.docstatus !== 1 || frm.perm?.[0]?.cancel) return;

	const { name, modified } = frm.doc;
	frappe.call({
		method: "hrms.api.approval.can_cancel_approved",
		args: { doctype: frm.doctype, name },
		callback: (r) => {
			// A reload since the question makes the answer stale.
			if (!r.message?.can_cancel || frm.doc.name !== name || frm.doc.modified !== modified)
				return;
			frm.add_custom_button(__("Cancel"), () => {
				frappe.confirm(__("Cancel this approved {0}?", [__(frm.doctype)]), () => {
					frappe.call({
						method: "hrms.api.approval.finalize",
						type: "POST",
						freeze: true,
						args: {
							doctype: frm.doctype,
							name,
							docstatus: 2,
							expected_modified: modified,
						},
						callback: () => {
							console.info("[approved_request_cancel] cancelled", frm.doctype, name);
							frm.reload_doc();
						},
					});
				});
			});
		},
	});
};

hrms.approved_request_cancel.APPROVED_CANCEL_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, { refresh: hrms.approved_request_cancel.setup });
});
