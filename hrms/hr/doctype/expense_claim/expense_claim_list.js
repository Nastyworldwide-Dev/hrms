// One word per state in Desk, as in Nadi (owner, 5 Oct 2026; hrms/public/js/request_status.bundle.js and
// frontend/src/utils/requestStatus.js). An expense claim has two parts, the decision (approval_status)
// and the money (status), so it has its own rule. The stored words are untouched.
//
// Frappe used to draw this pill from the doctype's own "states" list (Draft / Submitted / Unpaid ...),
// which outranks any list script; that list is now empty so this rule decides.
frappe.listview_settings["Expense Claim"] = {
	add_fields: ["company", "approval_status"],
	has_indicator_for_draft: 1,
	get_indicator: (doc) => {
		if (doc.docstatus === 0 || doc.docstatus === "0") return [__("Waiting"), "orange", "docstatus,=,0"];
		if (doc.docstatus === 2 || doc.docstatus === "2") return [__("Cancelled"), "red", "docstatus,=,2"];
		if (doc.approval_status === "Rejected" || doc.status === "Rejected") {
			return [__("Rejected"), "red", "approval_status,=,Rejected"];
		}
		if (doc.status === "Paid") return [__("Paid"), "green", "status,=,Paid"];
		// submitted and approved, money not paid out yet. The click filter is the DECISION, not the money
		// word: an approved claim with nothing sanctioned keeps the stored status "Submitted" (set_status),
		// and a filter on "Unpaid" would not list it (design review of 3f761024f).
		if (doc.approval_status === "Approved" || doc.status === "Unpaid") {
			return [__("Approved · unpaid"), "blue", "approval_status,=,Approved"];
		}
		// submitted with no decision recorded (an older row): waiting for the decision
		return [__("Waiting"), "orange", "docstatus,=,1"];
	},
};
