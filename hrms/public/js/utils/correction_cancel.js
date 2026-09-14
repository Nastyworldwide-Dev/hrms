// Desk "Cancel (correction)" for submitted no-decision requests — Nabil, 14 Sep 2026.
//
// Employee Advance, Travel Request and Compensatory Leave Request stay
// permission-locked: nobody holds write on them, so Desk's own Cancel is refused
// (Frappe checks write on every save, cancel included). HR Manager / System Manager
// reverse a mistake through hrms.api.correction_cancel.cancel_for_correction, which
// re-checks role, company fence, read access, docstatus and the reason on the
// server. The role check here only decides whether the button is shown.

frappe.provide("hrms.correction_cancel");

hrms.correction_cancel.setup = function (frm) {
	const allowed =
		frm.doc.docstatus === 1 &&
		(frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager"));
	if (!allowed) return;

	frm.add_custom_button(__("Cancel (correction)"), () => {
		frappe.prompt(
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason for the correction"),
				reqd: 1,
			},
			({ reason }) => {
				frappe.call({
					method: "hrms.api.correction_cancel.cancel_for_correction",
					type: "POST",
					freeze: true,
					args: {
						doctype: frm.doctype,
						name: frm.doc.name,
						reason,
						expected_modified: frm.doc.modified,
					},
					callback: () => {
						console.info("[correction_cancel] cancelled", frm.doctype, frm.doc.name);
						frm.reload_doc();
					},
				});
			},
			__("Cancel {0} for correction", [__(frm.doctype)]),
			__("Cancel document"),
		);
	});
};
